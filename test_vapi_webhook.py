from fastapi.testclient import TestClient

from vapi_server import app


client = TestClient(app)


def run_tests():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "toolcall-1",
                    "name": "get_available_slots",
                    "arguments": {
                        "count": 3,
                        "language": "es",
                    },
                }
            ],
        }
    }

    response = client.post("/tools/webhook", json=payload)
    print("POST /tools/webhook ->", response.status_code, response.json())


if __name__ == "__main__":
    run_tests()
