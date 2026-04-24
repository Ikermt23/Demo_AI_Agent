import json
import os
from datetime import datetime, timedelta

CALENDAR_FILE = "calendar.json"
LEADS_FILE = "leads.jsonl"

SCHEDULE = {
    0: ["10:00", "12:00", "17:00", "19:00"],  # Lunes
    1: ["10:00", "12:00", "17:00", "19:00"],  # Martes
    2: ["10:00", "12:00", "17:00", "19:00"],  # Miércoles
    3: ["10:00", "12:00", "17:00", "19:00"],  # Jueves
    4: ["10:00", "12:00", "17:00", "19:00"],  # Viernes
    5: ["11:00", "13:00"],                     # Sábado
    # Domingo (6): cerrado
}

DAY_NAMES = {
    0: "lunes", 1: "martes", 2: "miércoles",
    3: "jueves", 4: "viernes", 5: "sábado"
}


def generate_calendar(days_ahead=60):
    """Genera calendar.json con slots para los próximos N días.
    Preserva reservas existentes si el fichero ya existe."""
    existing_bookings = {}

    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
        for slot in old["slots"]:
            if slot["booked"]:
                key = f"{slot['fecha']}_{slot['hora']}"
                existing_bookings[key] = slot["user"]

    today = datetime.today().date()
    slots = []
    slot_id = 1

    for i in range(days_ahead):
        day = today + timedelta(days=i)
        weekday = day.weekday()

        if weekday not in SCHEDULE:
            continue

        for hora in SCHEDULE[weekday]:
            key = f"{day.isoformat()}_{hora}"
            slots.append({
                "id": f"slot_{slot_id:03d}",
                "fecha": day.isoformat(),
                "hora": hora,
                "dia_semana": DAY_NAMES[weekday],
                "booked": key in existing_bookings,
                "user": existing_bookings.get(key),
            })
            slot_id += 1

    calendar = {
        "slots": slots,
        "generated_at": datetime.now().isoformat(),
    }

    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(calendar, f, indent=2, ensure_ascii=False)

    return calendar


def get_available_slots(modalidad=None, count=3, **kwargs):
    """Devuelve los próximos N slots disponibles como lista de dicts."""
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        cal = json.load(f)

    today = datetime.today().date().isoformat()
    available = [
        {
            "fecha": s["fecha"],
            "hora": s["hora"],
            "dia_semana": s["dia_semana"],
        }
        for s in cal["slots"]
        if not s["booked"] and s["fecha"] >= today
    ]

    slots = available[:count]

    if not slots:
        return {"slots": [], "mensaje": "No hay huecos disponibles en los próximos 14 días."}

    return {"slots": slots}


def book_slot(fecha, hora, modalidad, nombre, email, telefono,
              pais_origen=None, estudios=None, fecha_estancia=None, **kwargs):
    """Reserva un slot y guarda el lead. Devuelve dict con resultado."""
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        cal = json.load(f)

    for slot in cal["slots"]:
        if slot["fecha"] == fecha and slot["hora"] == hora:
            if slot["booked"]:
                return {
                    "success": False,
                    "error": "Ese hueco ya está reservado. Llama a get_available_slots para ofrecer opciones actualizadas.",
                }

            user_data = {
                "nombre": nombre,
                "email": email,
                "telefono": telefono,
                "modalidad": modalidad,
                "pais_origen": pais_origen,
                "estudios": estudios,
                "fecha_estancia": fecha_estancia,
                "reservado_en": datetime.now().isoformat(),
            }

            slot["booked"] = True
            slot["user"] = user_data

            with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
                json.dump(cal, f, indent=2, ensure_ascii=False)

            _save_lead(fecha, hora, modalidad, user_data)

            return {
                "success": True,
                "mensaje": f"Reserva confirmada: {slot['dia_semana'].capitalize()} {fecha} a las {hora} ({modalidad}).",
            }

    return {
        "success": False,
        "error": "No se encontró ese hueco en el calendario. Llama a get_available_slots para ver opciones reales.",
    }


def _save_lead(fecha, hora, modalidad, user_data):
    lead = {
        "nombre": user_data.get("nombre"),
        "email": user_data.get("email"),
        "telefono": user_data.get("telefono"),
        "pais_origen": user_data.get("pais_origen"),
        "estudios": user_data.get("estudios"),
        "fecha_estancia": user_data.get("fecha_estancia"),
        "visita": {
            "fecha": fecha,
            "hora": hora,
            "modalidad": modalidad,
        },
        "timestamp": user_data.get("reservado_en"),
    }
    with open(LEADS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(lead, ensure_ascii=False) + "\n")


def _should_regenerate():
    if not os.path.exists(CALENDAR_FILE):
        return True
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        cal = json.load(f)
    generated = cal.get("generated_at", "")
    if not generated:
        return True
    if datetime.fromisoformat(generated).date() < datetime.today().date():
        return True
    today = datetime.today().date().isoformat()
    available = [s for s in cal["slots"] if not s["booked"] and s["fecha"] >= today]
    return len(available) == 0


if _should_regenerate():
    generate_calendar()
