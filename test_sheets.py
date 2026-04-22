import argparse
import json

from dotenv import load_dotenv

from sheets_utils import test_sheets_connection


def main():
    parser = argparse.ArgumentParser(
        description="Comprueba acceso a Google Sheets para UniLiving."
    )
    parser.add_argument(
        "--write-test",
        action="store_true",
        help="Añade una fila de prueba a la hoja para validar permisos de escritura.",
    )
    args = parser.parse_args()

    load_dotenv()
    result = test_sheets_connection(write_test=args.write_test)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
