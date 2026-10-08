from fastapi import FastAPI

from app.config import Settings

app = FastAPI(title="HomeFlow Agent API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
