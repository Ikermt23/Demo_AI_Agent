from calendar_utils import book_slot, get_available_slots
from email_utils import send_booking_email
from sheets_utils import save_lead_sheets


def get_slots_for_channel(count=3):
    """Devuelve huecos listos para chat o voz."""
    return get_available_slots(count=count)


def complete_booking(data):
    """Reserva, guarda en Sheets y envia email sin romper el flujo."""
    booking_result = book_slot(**data)
    result = {
        "success": booking_result.get("success", False),
        "booking": booking_result,
        "sheets": None,
        "email": None,
    }

    if not booking_result.get("success"):
        return result

    result["sheets"] = save_lead_sheets(data)
    result["email"] = send_booking_email(data)
    return result
