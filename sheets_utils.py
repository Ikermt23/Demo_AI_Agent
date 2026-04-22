import json
import os
from datetime import datetime

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound


DEFAULT_CREDENTIALS_FILE = "credentials.json"


def _credentials_path():
    return os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", DEFAULT_CREDENTIALS_FILE)


def _load_credentials_metadata():
    path = _credentials_path()

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No se encontró el fichero de credenciales: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return {
        "path": path,
        "client_email": raw.get("client_email", ""),
        "project_id": raw.get("project_id", ""),
    }


def _get_connection_context():
    meta = _load_credentials_metadata()
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip()

    if not spreadsheet_id:
        raise RuntimeError("Falta SPREADSHEET_ID en el archivo .env")

    return {
        "credentials_path": meta["path"],
        "client_email": meta["client_email"],
        "project_id": meta["project_id"],
        "spreadsheet_id": spreadsheet_id,
    }


def _log_connection_context(prefix, context):
    print(
        f"{prefix} credentials={context['credentials_path']} "
        f"client_email={context['client_email']} "
        f"spreadsheet_id={context['spreadsheet_id']}"
    )


def _build_error_message(error, context):
    if isinstance(error, FileNotFoundError):
        return str(error)

    if isinstance(error, RuntimeError):
        return str(error)

    if isinstance(error, SpreadsheetNotFound):
        return (
            "No se encontró la hoja o esta cuenta no tiene acceso. "
            f"Comparte la hoja con {context['client_email']} como Editor y revisa SPREADSHEET_ID."
        )

    if isinstance(error, WorksheetNotFound):
        return "La hoja existe, pero no se encontró la primera pestaña (sheet1)."

    if isinstance(error, APIError):
        status_code = getattr(error.response, "status_code", None)
        api_text = ""
        try:
            api_text = error.response.text
        except Exception:
            api_text = str(error)

        if status_code == 403:
            return (
                "Google Sheets devolvió 403 Forbidden. La cuenta del service account "
                f"activa es {context['client_email']}. Comparte la hoja con ese correo "
                "como Editor o revisa si el rango/pestaña está protegido. "
                f"Respuesta API: {api_text}"
            )

        if status_code == 404:
            return (
                "Google Sheets devolvió 404. Revisa que SPREADSHEET_ID sea correcto "
                f"y que la hoja exista. Respuesta API: {api_text}"
            )

        return f"Error de Google Sheets ({status_code}): {api_text}"

    return f"{type(error).__name__}: {error}"


def _get_sheet():
    context = _get_connection_context()
    _log_connection_context("[SHEETS] Intentando conectar.", context)

    gc = gspread.service_account(filename=context["credentials_path"])
    spreadsheet = gc.open_by_key(context["spreadsheet_id"])
    sheet = spreadsheet.sheet1

    return sheet, context


def build_lead_row(data):
    return [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        data.get("nombre", ""),
        data.get("email", ""),
        data.get("telefono", ""),
        data.get("pais_origen", ""),
        data.get("estudios", ""),
        data.get("fecha_estancia", ""),
        data.get("fecha", ""),
        data.get("hora", ""),
        data.get("modalidad", ""),
    ]


def save_lead_sheets(data):
    """Añade una fila con los datos del lead a Google Sheets sin romper el chat."""
    try:
        sheet, context = _get_sheet()
        row = build_lead_row(data)
        sheet.append_row(row)
        print(
            f"[SHEETS] Lead guardado correctamente en '{sheet.title}' "
            f"con {context['client_email']}: {row}"
        )
        return {
            "success": True,
            "worksheet": sheet.title,
            "client_email": context["client_email"],
        }
    except Exception as error:
        try:
            context = _get_connection_context()
        except Exception as context_error:
            context = {
                "client_email": "desconocido",
                "spreadsheet_id": os.getenv("SPREADSHEET_ID", "").strip(),
            }
            message = _build_error_message(context_error, context)
            print(f"[SHEETS ERROR] {message}")
            return {"success": False, "error": message}

        message = _build_error_message(error, context)
        print(f"[SHEETS ERROR] {message}")
        return {"success": False, "error": message}


def test_sheets_connection(write_test=False):
    """Verifica acceso a Google Sheets; opcionalmente hace una escritura de prueba."""
    try:
        sheet, context = _get_sheet()
        info = {
            "success": True,
            "client_email": context["client_email"],
            "spreadsheet_id": context["spreadsheet_id"],
            "worksheet": sheet.title,
        }

        if write_test:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "[TEST] Codex",
                "test@example.com",
                "600000000",
                "España",
                "Testing",
                "septiembre-junio",
                datetime.now().date().isoformat(),
                "10:00",
                "videollamada",
            ]
            sheet.append_row(row)
            info["write_test"] = "ok"
            print(f"[SHEETS TEST] Escritura de prueba correcta: {row}")
        else:
            info["write_test"] = "skipped"
            print(
                f"[SHEETS TEST] Acceso de lectura correcto a '{sheet.title}' "
                f"con {context['client_email']}"
            )

        return info
    except Exception as error:
        try:
            context = _get_connection_context()
        except Exception as context_error:
            context = {
                "client_email": "desconocido",
                "spreadsheet_id": os.getenv("SPREADSHEET_ID", "").strip(),
            }
            message = _build_error_message(context_error, context)
            print(f"[SHEETS TEST ERROR] {message}")
            return {"success": False, "error": message}

        message = _build_error_message(error, context)
        print(f"[SHEETS TEST ERROR] {message}")
        return {"success": False, "error": message}
