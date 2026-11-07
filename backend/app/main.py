"""
FastAPI application entrypoint.

CORS is scoped tightly to the known frontend origin(s) from settings —
even though this never leaves localhost/the Docker network, we keep the
habit of an explicit allow-list rather than "*".
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, chat, climate, disease, prices

app = FastAPI(
    title="Mifugo AI API",
    description=(
        "Offline-first livestock market intelligence API for Turkana County. "
        "Consumed by the separate React/Vite frontend (port 5173)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prices.router)
app.include_router(chat.router)
app.include_router(climate.router)
app.include_router(disease.router)
app.include_router(alerts.router)


@app.get("/health")
def health():
    """Simple liveness check — also useful for the frontend to detect
    whether the backend container is up before showing the login form."""
    return {"status": "ok", "env": settings.app_env}
