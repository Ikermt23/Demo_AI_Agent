from typing import Any, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from booking_service import complete_booking, get_slots_for_channel


app = FastAPI(title="UniLiving Voice API", version="1.0.0")


class SlotsRequest(BaseModel):
    count: int = 3
    language: Literal["es", "en"] = "es"


class BookingRequest(BaseModel):
    fecha: str
    hora: str
    modalidad: Literal["presencial", "videollamada"]
    nombre: str
    email: str
    telefono: str
    pais_origen: Optional[str] = None
    estudios: Optional[str] = None
    fecha_estancia: Optional[str] = None
    language: Literal["es", "en"] = "es"


class VapiToolCallItem(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = {}


class VapiToolMessage(BaseModel):
    type: str
    toolCallList: list[VapiToolCallItem] = []


class VapiToolWebhookRequest(BaseModel):
    message: VapiToolMessage


@app.get("/health")
def health():
    return {"ok": True, "service": "uniliving-voice-api"}


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "uniliving-voice-api",
        "message": "UniLiving voice backend is running.",
        "routes": [
            "/health",
            "/docs",
            "/tools/get-available-slots",
            "/tools/book-visit",
            "/tools/webhook",
        ],
    }


@app.post("/tools/get-available-slots")
def get_available_slots_tool(payload: SlotsRequest):
    data = get_slots_for_channel(count=payload.count)
    slots = data.get("slots", [])

    if payload.language == "en":
        message = (
            "These are the next available visit slots."
            if slots
            else "There are no available visit slots in the next few days."
        )
    else:
        message = (
            "Estos son los proximos huecos disponibles para visita."
            if slots
            else "No hay huecos disponibles en los proximos dias."
        )

    return {
        "success": bool(slots),
        "message": message,
        "slots": slots,
    }


@app.post("/tools/book-visit")
def book_visit_tool(payload: BookingRequest):
    booking_data = payload.model_dump()
    language = booking_data.pop("language", "es")
    result = complete_booking(booking_data)

    if result["success"]:
        if language == "en":
            message = "Visit booked successfully."
            if result.get("email", {}).get("success"):
                message += " Confirmation email sent."
        else:
            message = "Visita reservada correctamente."
            if result.get("email", {}).get("success"):
                message += " Email de confirmacion enviado."
    else:
        if language == "en":
            message = result["booking"].get(
                "error",
                "The selected slot is no longer available.",
            )
        else:
            message = result["booking"].get(
                "error",
                "El hueco seleccionado ya no esta disponible.",
            )

    return {
        "success": result["success"],
        "message": message,
        "booking": result["booking"],
        "sheets": result.get("sheets"),
        "email": result.get("email"),
    }


def _format_slots_result(language: str, slots: list[dict[str, str]]):
    if not slots:
        if language == "en":
            return "There are no available visit slots in the next few days."
        return "No hay huecos disponibles en los proximos dias."

    if language == "en":
        intro = "Next available visit slots: "
    else:
        intro = "Proximos huecos disponibles para visita: "

    slot_text = "; ".join(
        f"{slot['dia_semana']} {slot['fecha']} at {slot['hora']}"
        if language == "en"
        else f"{slot['dia_semana']} {slot['fecha']} a las {slot['hora']}"
        for slot in slots
    )
    return intro + slot_text


@app.post("/tools/webhook")
def vapi_tools_webhook(payload: VapiToolWebhookRequest):
    results = []

    for tool_call in payload.message.toolCallList:
        arguments = tool_call.arguments or {}
        language = arguments.get("language", "es")

        if tool_call.name == "get_available_slots":
            count = int(arguments.get("count", 3))
            slots_data = get_slots_for_channel(count=count)
            result_text = _format_slots_result(language, slots_data.get("slots", []))
        elif tool_call.name == "book_visit":
            booking_result = complete_booking(arguments)
            if booking_result["success"]:
                if language == "en":
                    result_text = "Visit booked successfully."
                    if (booking_result.get("email") or {}).get("success"):
                        result_text += " Confirmation email sent."
                else:
                    result_text = "Visita reservada correctamente."
                    if (booking_result.get("email") or {}).get("success"):
                        result_text += " Email de confirmacion enviado."
            else:
                result_text = booking_result["booking"].get(
                    "error",
                    "No se pudo completar la reserva.",
                )
        else:
            result_text = f"Tool no reconocida: {tool_call.name}"

        results.append(
            {
                "toolCallId": tool_call.id,
                "result": result_text,
            }
        )

    return {"results": results}
