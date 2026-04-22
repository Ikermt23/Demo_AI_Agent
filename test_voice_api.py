from fastapi.testclient import TestClient

from vapi_server import app


client = TestClient(app)


def run_tests():
    health = client.get("/health")
    slots = client.post("/tools/get-available-slots", json={"count": 3, "language": "es"})

    print("GET /health ->", health.status_code, health.json())
    print("POST /tools/get-available-slots ->", slots.status_code, slots.json())


if __name__ == "__main__":
    run_tests()
