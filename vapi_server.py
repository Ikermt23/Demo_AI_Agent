from fastapi import FastAPI
from voice_api import router as voice_router


app = FastAPI(title="UniLiving Voice API", version="1.0.0")
app.include_router(voice_router)


@app.get("/health")
def health():
    return {"ok": True, "service": "uniliving-voice-api"}


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "uniliving-voice-api",
        "message": "UniLiving voice backend is running.",
        "routes": [
            "/health",
            "/docs",
            "/tools/get-available-slots",
            "/tools/book-visit",
            "/tools/webhook",
        ],
    }
