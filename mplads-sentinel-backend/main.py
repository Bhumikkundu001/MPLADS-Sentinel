import os
from app.api.auth import router as auth_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine
from app.models import Work, WorkSimilarity  # noqa: F401 — ensures tables are registered
from app.database import Base
from app.api import works, risk, analytics, alerts, copilot

load_dotenv()

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MPLADS Sentinel API",
    description="AI-powered monitoring platform for MPLADS works",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(works.router,    prefix="/works",     tags=["Works"])
app.include_router(risk.router,     prefix="/risk",      tags=["Risk"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(alerts.router,   prefix="/alerts",    tags=["Alerts"])
app.include_router(copilot.router,  prefix="/copilot",   tags=["Copilot"])
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "MPLADS Sentinel API"}
