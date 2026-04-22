import asyncio
import json
import logging
import os
import re

import chainlit as cl
from dotenv import load_dotenv
from openai import AsyncOpenAI

try:
    from langdetect import DetectorFactory
    from langdetect import detect as _langdetect
except Exception:  # pragma: no cover - fallback if optional dependency is missing
    DetectorFactory = None
    _langdetect = None

from booking_service import complete_booking, get_slots_for_channel

if DetectorFactory is not None:
    DetectorFactory.seed = 0  # resultados deterministas

_ES_WORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'de', 'que', 'y', 'es', 'soy',
    'voy', 'me', 'mi', 'tu', 'su', 'como', 'pero', 'por', 'para', 'con',
    'hay', 'tengo', 'quiero', 'hola', 'gracias', 'cuando', 'donde', 'estoy',
    'este', 'esta', 'ese', 'porque', 'aunque', 'tambien', 'desde', 'hasta',
    'cuanto', 'cuantos', 'busco', 'necesito',
}
_EN_WORDS = {
    'the', 'is', 'are', 'am', 'im', 'my', 'your', 'we', 'it', 'in', 'to',
    'and', 'or', 'going', 'gonna', 'will', 'can', 'have', 'has', 'do',
    'does', 'hello', 'hi', 'study', 'studying', 'from', 'what', 'when',
    'where', 'who', 'that', 'this', 'at', 'for', 'of', 'with', 'about',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december', 'university', 'an',
    'looking', 'interested', 'need', 'want', 'would', 'could', 'should',
    'name', 'room', 'price', 'visit', 'book', 'available',
}

load_dotenv()

logger = logging.getLogger("uniliving.chat")
_client = None

with open("prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def _is_env_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def get_runtime_checks():
    return {
        "groq_api_key": _is_env_set("GROQ_API_KEY"),
        "spreadsheet_id": _is_env_set("SPREADSHEET_ID"),
        "google_credentials_json": _is_env_set("GOOGLE_CREDENTIALS_JSON"),
        "google_sheets_credentials_file": _is_env_set("GOOGLE_SHEETS_CREDENTIALS_FILE"),
        "email_enabled": os.getenv("EMAIL_ENABLED", "false").strip().lower() == "true",
    }


def get_llm_client():
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY en el entorno del servidor.")

    _client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    return _client


def detect_language(text: str, current_lang: str = "es") -> str:
    clean = text.strip()

    # Caracteres españoles exclusivos → español seguro
    if any(c in clean for c in "áéíóúñüÁÉÍÓÚÑÜ¿¡"):
        return "es"

    words = set(re.findall(r"\b\w+\b", clean.lower()))
    en_score = len(words & _EN_WORDS)
    es_score = len(words & _ES_WORDS)

    if en_score > es_score:
        return "en"
    if es_score > en_score:
        return "es"

    # Sin ganador claro: langdetect si hay texto suficiente
    if len(clean) >= 10 and _langdetect is not None:
        try:
            return "en" if _langdetect(clean) == "en" else "es"
        except Exception:
            pass

    return current_lang


def build_messages(history, lang: str = "es"):
    slots_data = get_slots_for_channel(3)
    slots = slots_data.get("slots", [])

    if slots:
        slots_lines = "\n".join(
            f"- {slot['dia_semana'].capitalize()} {slot['fecha']} a las {slot['hora']}"
            for slot in slots
        )
        slot_section = (
            "\n\n# HUECOS DISPONIBLES AHORA MISMO\n"
            "(Usa exactamente estos cuando el usuario quiera visita. No inventes otros.)\n"
            + slots_lines
        )
    else:
        slot_section = (
            "\n\n# HUECOS DISPONIBLES: No hay huecos disponibles en los proximos dias."
        )

    if lang == "en":
        lang_override = "\n\n# INSTRUCCIÓN OBLIGATORIA PARA ESTE TURNO\nEl último mensaje del usuario está en INGLÉS. Responde ÚNICAMENTE en inglés. Ni una palabra en español."
    else:
        lang_override = "\n\n# INSTRUCCIÓN OBLIGATORIA PARA ESTE TURNO\nEl último mensaje del usuario está en ESPAÑOL. Responde ÚNICAMENTE en español. Ni una palabra en inglés."

    system_msg = {"role": "system", "content": SYSTEM_PROMPT + slot_section + lang_override}
    return [system_msg] + history


async def call_llm(messages):
    client = get_llm_client()
    for attempt in range(3):
        try:
            return await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
            )
        except Exception as error:
            if "429" in str(error) and attempt < 2:
                wait = 5 * (attempt + 1)
                print(f"[WARN] Rate limit, esperando {wait}s...")
                await asyncio.sleep(wait)
                continue
            raise


@cl.on_chat_start
async def start():
    logger.info("Nueva sesion de chat. checks=%s", get_runtime_checks())
    cl.user_session.set("history", [])
    cl.user_session.set("lang", "es")
    await cl.Message(
        content=(
            "¡Hola! Soy Alex de UniLiving Barcelona 👋\n"
            "¿Cómo te llamas?"
        )
    ).send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})

    try:
        current_lang = cl.user_session.get("lang", "es")
        lang = detect_language(message.content, current_lang)
        cl.user_session.set("lang", lang)
        messages = build_messages(history, lang)
        response = await call_llm(messages)
        reply = response.choices[0].message.content or ""

        if "<BOOKING>" in reply:
            reply = _process_booking(reply)

        history.append({"role": "assistant", "content": reply})
        cl.user_session.set("history", history)
        await cl.Message(content=reply).send()

    except Exception as error:
        logger.exception(
            "Error procesando mensaje. lang=%s history_len=%s last_user_message=%r",
            cl.user_session.get("lang", "es"),
            len(history),
            message.content[:300],
        )
        history.pop()
        cl.user_session.set("history", history)
        await cl.Message(
            content=(
                "Uy, algo ha fallado por mi lado al procesar tu mensaje "
                f"({type(error).__name__}). Puedes repetir lo que me decias?"
            )
        ).send()


def _process_booking(reply):
    """Extrae el bloque <BOOKING>, ejecuta la reserva y devuelve el mensaje limpio."""
    visible = reply.split("<BOOKING>")[0].strip()

    try:
        json_str = reply.split("<BOOKING>")[1].split("</BOOKING>")[0].strip()
        data = json.loads(json_str)
        result = complete_booking(data)
        print(f"[BOOKING] {data} -> {result['booking']}")

        if result.get("success"):
            sheets_result = result.get("sheets") or {}
            email_result = result.get("email") or {}

            if email_result.get("success"):
                visible += "\n\nTambien te acabo de enviar un email con la confirmacion."

            if not sheets_result.get("success"):
                print(
                    f"[BOOKING WARNING] Sheets no guardado: {sheets_result.get('error', '')}"
                )

            if not email_result.get("success") and not email_result.get("skipped"):
                print(
                    f"[BOOKING WARNING] Email no enviado: {email_result.get('error', '')}"
                )
        else:
            visible += f"\n\n(Hubo un problema al reservar: {result['booking'].get('error', '')})"
    except Exception as error:
        logger.exception("Error procesando booking.")

    return visible
