from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth
from src.api import user

app = FastAPI(
    title="Appointment Booking API",
    description="API for an appointment booking system. Provides authentication, registration, and role-based model for patients and doctors.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)

@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}
