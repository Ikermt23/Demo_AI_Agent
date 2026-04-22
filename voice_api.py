from typing import Any, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from booking_service import complete_booking, get_slots_for_channel


router = APIRouter(tags=["voice"])


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
    arguments: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class VapiNestedToolCall(BaseModel):
    id: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class VapiToolWithToolCallItem(BaseModel):
    name: str
    toolCall: VapiNestedToolCall
    model_config = ConfigDict(extra="allow")


class VapiToolMessage(BaseModel):
    type: str
    toolCallList: list[VapiToolCallItem] = Field(default_factory=list)
    toolWithToolCallList: list[VapiToolWithToolCallItem] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class VapiToolWebhookRequest(BaseModel):
    message: VapiToolMessage
    model_config = ConfigDict(extra="allow")


def _tool_args(arguments: dict[str, Any], parameters: dict[str, Any]):
    return parameters or arguments or {}


def _format_slots_result(language: str, slots: list[dict[str, str]]):
    if not slots:
        if language == "en":
            return "There are no available visit slots in the next few days."
        return "No hay huecos disponibles en los proximos dias."

    intro = (
        "Next available visit slots: "
        if language == "en"
        else "Proximos huecos disponibles para visita: "
    )
    slot_text = "; ".join(
        f"{slot['dia_semana']} {slot['fecha']} at {slot['hora']}"
        if language == "en"
        else f"{slot['dia_semana']} {slot['fecha']} a las {slot['hora']}"
        for slot in slots
    )
    return intro + slot_text


def _iter_tool_calls(message: VapiToolMessage):
    for tool_call in message.toolCallList:
        yield {
            "id": tool_call.id,
            "name": tool_call.name,
            "arguments": _tool_args(tool_call.arguments, tool_call.parameters),
        }

    for tool in message.toolWithToolCallList:
        yield {
            "id": tool.toolCall.id,
            "name": tool.name,
            "arguments": _tool_args(
                tool.toolCall.arguments,
                tool.toolCall.parameters,
            ),
        }


@router.post("/tools/get-available-slots")
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


@router.post("/tools/book-visit")
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


@router.post("/tools/webhook")
def vapi_tools_webhook(payload: VapiToolWebhookRequest):
    if payload.message.type != "tool-calls":
        return {"ok": True, "ignored": payload.message.type}

    results = []

    for tool_call in _iter_tool_calls(payload.message):
        arguments = tool_call["arguments"] or {}
        language = arguments.get("language", "es")

        if tool_call["name"] == "get_available_slots":
            count = int(arguments.get("count", 3))
            slots_data = get_slots_for_channel(count=count)
            result_text = _format_slots_result(language, slots_data.get("slots", []))
        elif tool_call["name"] == "book_visit":
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
            result_text = f"Tool no reconocida: {tool_call['name']}"

        results.append(
            {
                "name": tool_call["name"],
                "toolCallId": tool_call["id"],
                "result": result_text,
            }
        )

    return {"results": results}
