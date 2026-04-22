import json

from dotenv import load_dotenv

from email_utils import is_email_enabled, send_booking_email


def main():
    load_dotenv()

    sample_data = {
        "fecha": "2026-04-23",
        "hora": "10:00",
        "modalidad": "presencial",
        "nombre": "Iker Pichaco Miguel",
        "email": "pichacoiker@gmail.com",
        "telefono": "633562838",
        "pais_origen": "Panama",
        "estudios": "Enfermeria en la URV",
        "fecha_estancia": "septiembre-junio",
    }

    if not is_email_enabled():
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "EMAIL_ENABLED=false o faltan variables SMTP en .env",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = send_booking_email(sample_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
