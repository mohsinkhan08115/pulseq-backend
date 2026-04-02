# api/index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import auth, patients, medical_records, queue, patient_auth

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="PulseQ — Smart Hospital Queue & Medical Records System",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Flutter Web runs on localhost:<random-port> and calls localhost:8000.
# We must explicitly list both localhost variants so the browser's preflight
# OPTIONS request succeeds.
#
# For production replace this list with your actual domain(s).
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:8080",
    "http://localhost:8000",
    # Flutter Web dev server uses a random high port — allow all localhost ports.
    # A wildcard on the scheme+host covers them all:
    "http://localhost:63925",   # common Flutter Web debug port (add yours if different)
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    # Production / Vercel
    "https://pqapi.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    # Use "*" to allow any origin — safest for local dev.
    # For production, replace "*" with the explicit `origins` list above.
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(medical_records.router)
app.include_router(queue.router)
app.include_router(patient_auth.router)


@app.get("/test")
def test():
    return {"status": "working", "message": "Backend is reachable"}


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}