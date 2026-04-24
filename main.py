import os

from fastapi import FastAPI

from chainlit.utils import mount_chainlit
from dotenv import load_dotenv

from app import get_runtime_checks
from voice_api import router as voice_router


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

app = FastAPI(title="UniLiving Demo App", version="1.0.0")
app.include_router(voice_router)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "uniliving-demo-app",
        "checks": get_runtime_checks(),
    }


@app.get("/admin/reset-calendar")
def reset_calendar():
    from calendar_utils import generate_calendar
    cal = generate_calendar()
    available = [s for s in cal["slots"] if not s["booked"]]
    return {"ok": True, "total_slots": len(cal["slots"]), "available": len(available)}


mount_chainlit(app, os.path.join(BASE_DIR, "app.py"), path="/")
