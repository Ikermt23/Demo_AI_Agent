from typing import Any, Dict, Optional
from fastapi import APIRouter
from booking_service import complete_booking, get_slots_for_channel

router = APIRouter(tags=["voice"])


def _slots_text(slots: list, language: str = "es") -> str:
    if not slots:
        return (
            "There are no available visit slots in the next few days."
            if language == "en"
            else "No hay huecos disponibles en los proximos dias."
        )
    lines = "; ".join(
        f"{s['dia_semana']} {s['fecha']} at {s['hora']}"
        if language == "en"
        else f"{s['dia_semana']} {s['fecha']} a las {s['hora']}"
        for s in slots
    )
    return (
        f"Available slots: {lines}"
        if language == "en"
        else f"Huecos disponibles: {lines}"
    )


# ── ElevenLabs sends parameters directly in the JSON body ──────────────────

@router.post("/tools/get-available-slots")
def get_slots_tool(body: Dict[str, Any] = {}):
    """ElevenLabs llama a este endpoint cuando el agente quiere ver huecos."""
    count = int(body.get("count", 3))
    language = str(body.get("language", "es"))

    data = get_slots_for_channel(count=count)
    slots = data.get("slots", [])

    return {"result": _slots_text(slots, language)}


@router.post("/tools/book-visit")
def book_visit_tool(body: Dict[str, Any] = {}):
    """ElevenLabs llama a este endpoint cuando el agente quiere reservar."""
    language = str(body.pop("language", "es"))

    required = ["fecha", "hora", "modalidad", "nombre", "email", "telefono"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return {
            "result": (
                f"Missing required fields: {', '.join(missing)}. Ask the user for them."
                if language == "en"
                else f"Faltan datos obligatorios: {', '.join(missing)}. Preguntaselos al usuario."
            )
        }

    try:
        result = complete_booking(body)
    except Exception as e:
        print(f"[BOOK ERROR] {e}")
        return {"result": "Error interno al reservar." if language != "en" else "Internal booking error."}

    if result["success"]:
        msg = (
            "Visit booked successfully."
            if language == "en"
            else "Visita reservada correctamente."
        )
        if (result.get("email") or {}).get("success"):
            msg += (
                " Confirmation email sent."
                if language == "en"
                else " Email de confirmacion enviado."
            )
    else:
        msg = result["booking"].get(
            "error",
            "Slot no longer available." if language == "en" else "El hueco ya no esta disponible.",
        )

    return {"result": msg}
