from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth
from src.api import user
from src.api import doctor
from src.api import timeslot
from src.api import appointment
from src.api import notification

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
app.include_router(doctor.router)
app.include_router(timeslot.router)
app.include_router(appointment.router)
app.include_router(notification.router)  # Register notification endpoints

@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}
