from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import conversations, tours, webhook
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Agente de Turismo Lençóis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(tours.router)
app.include_router(conversations.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
