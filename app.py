import asyncio
import json
import os

import chainlit as cl
from dotenv import load_dotenv
from openai import AsyncOpenAI

from calendar_utils import book_slot, get_available_slots
from email_utils import send_booking_email
from sheets_utils import save_lead_sheets

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

with open("prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def build_messages(history):
    slots_data = get_available_slots(3)
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

    system_msg = {"role": "system", "content": SYSTEM_PROMPT + slot_section}
    return [system_msg] + history


async def call_llm(messages):
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
    cl.user_session.set("history", [])
    await cl.Message(
        content=(
            "Hola! I'm Alex from UniLiving Barcelona. "
            "Puedo ayudarte en espanol or English. What's your name?"
        )
    ).send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})

    try:
        messages = build_messages(history)
        response = await call_llm(messages)
        reply = response.choices[0].message.content or ""

        if "<BOOKING>" in reply:
            reply = _process_booking(reply)

        history.append({"role": "assistant", "content": reply})
        cl.user_session.set("history", history)
        await cl.Message(content=reply).send()

    except Exception as error:
        print(f"[ERROR] {error}")
        history.pop()
        cl.user_session.set("history", history)
        await cl.Message(
            content="Uy, algo ha fallado por mi lado. Puedes repetir lo que me decias?"
        ).send()


def _process_booking(reply):
    """Extrae el bloque <BOOKING>, ejecuta la reserva y devuelve el mensaje limpio."""
    visible = reply.split("<BOOKING>")[0].strip()

    try:
        json_str = reply.split("<BOOKING>")[1].split("</BOOKING>")[0].strip()
        data = json.loads(json_str)
        result = book_slot(**data)
        print(f"[BOOKING] {data} -> {result}")

        if result.get("success"):
            sheets_result = save_lead_sheets(data)
            email_result = send_booking_email(data)

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
            visible += f"\n\n(Hubo un problema al reservar: {result.get('error', '')})"
    except Exception as error:
        print(f"[ERROR] procesando booking: {error}")

    return visible
