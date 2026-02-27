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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(medical_records.router)
app.include_router(queue.router)
app.include_router(patient_auth.router)

@app.get("/test")
def test():
    return {"status": "working"}

@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}