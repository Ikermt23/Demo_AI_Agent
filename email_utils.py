import os
import smtplib
from datetime import datetime
from email.message import EmailMessage


DAY_NAMES = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo",
}


def is_email_enabled():
    required = [
        os.getenv("SMTP_HOST", "").strip(),
        os.getenv("SMTP_PORT", "").strip(),
        os.getenv("SMTP_USER", "").strip(),
        os.getenv("SMTP_PASSWORD", "").strip(),
        os.getenv("EMAIL_FROM", "").strip(),
    ]
    enabled_flag = os.getenv("EMAIL_ENABLED", "false").strip().lower() == "true"
    return enabled_flag and all(required)


def _format_booking_date(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    day_name = DAY_NAMES[dt.weekday()]
    return f"{day_name.capitalize()} {dt.strftime('%d/%m/%Y')} a las {dt.strftime('%H:%M')}"


def _build_subject(data):
    return f"Confirmacion de visita - UniLiving Barcelona - {data.get('fecha', '')} {data.get('hora', '')}"


def _build_text_body(data):
    booking_label = _format_booking_date(data["fecha"], data["hora"])
    modalidad = data.get("modalidad", "visita")
    nombre = data.get("nombre", "Hola")

    return f"""Hola {nombre},

    Tu visita con UniLiving Barcelona ha quedado confirmada.

Detalles de la cita:
- Fecha y hora: {booking_label}
- Modalidad: {modalidad}
- Email de contacto: {data.get('email', '')}
- Telefono: {data.get('telefono', '')}

Si necesitas cambiar la cita, responde a este email y te ayudamos.

Equipo UniLiving Barcelona
"""


def _build_html_body(data):
    booking_label = _format_booking_date(data["fecha"], data["hora"])
    modalidad = data.get("modalidad", "visita").capitalize()
    nombre = data.get("nombre", "Hola")

    return f"""\
<html>
  <body style="font-family: Arial, sans-serif; background:#f7f4ef; color:#1f2937; padding:24px;">
    <div style="max-width:640px; margin:0 auto; background:#ffffff; border-radius:16px; padding:32px; border:1px solid #eadfce;">
      <p style="margin:0 0 12px; font-size:14px; color:#8a6f4d;">UniLiving Barcelona</p>
      <h1 style="margin:0 0 16px; font-size:28px; color:#152238;">Tu visita esta confirmada</h1>
      <p style="font-size:16px; line-height:1.6;">Hola {nombre}, gracias por reservar con nosotros. Aqui tienes los detalles de tu cita.</p>

      <div style="margin:24px 0; background:#f9f7f2; border-radius:12px; padding:20px; border:1px solid #eee4d5;">
        <p style="margin:0 0 10px;"><strong>Fecha y hora:</strong> {booking_label}</p>
        <p style="margin:0 0 10px;"><strong>Modalidad:</strong> {modalidad}</p>
        <p style="margin:0 0 10px;"><strong>Email:</strong> {data.get('email', '')}</p>
        <p style="margin:0;"><strong>Telefono:</strong> {data.get('telefono', '')}</p>
      </div>

      <p style="font-size:15px; line-height:1.6;">Si necesitas mover la cita, responde a este email y te ayudamos.</p>
      <p style="margin-top:24px; font-size:15px;">Nos vemos pronto,<br><strong>Equipo UniLiving Barcelona</strong></p>
    </div>
  </body>
</html>
"""


def send_booking_email(data):
    """Envia email de confirmacion. Si no esta configurado, devuelve skip."""
    if not is_email_enabled():
        message = "Email desactivado o incompleto en .env. No se envia confirmacion."
        print(f"[EMAIL] {message}")
        return {"success": False, "skipped": True, "error": message}

    recipient = data.get("email", "").strip()
    if not recipient:
        message = "El lead no tiene email. No se envia confirmacion."
        print(f"[EMAIL] {message}")
        return {"success": False, "skipped": True, "error": message}

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip()
    from_name = os.getenv("EMAIL_FROM_NAME", "UniLiving Barcelona").strip()

    msg = EmailMessage()
    msg["Subject"] = _build_subject(data)
    msg["From"] = f"{from_name} <{email_from}>"
    msg["To"] = recipient
    msg.set_content(_build_text_body(data))
    msg.add_alternative(_build_html_body(data), subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print(f"[EMAIL] Confirmacion enviada correctamente a {recipient}")
        return {"success": True, "recipient": recipient}
    except Exception as error:
        print(f"[EMAIL ERROR] {type(error).__name__}: {error}")
        return {"success": False, "error": str(error), "recipient": recipient}
