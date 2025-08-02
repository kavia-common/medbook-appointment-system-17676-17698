"""Core SQLAlchemy ORM models for appointment booking app."""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

# --- Enum definitions ---
class UserTypeEnum(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"

class AppointmentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class NotificationTypeEnum(str, enum.Enum):
    APPOINTMENT_REQUEST = "appointment_request"
    APPOINTMENT_UPDATE = "appointment_update"
    GENERAL = "general"

# --- User model ---
class User(Base):
    """User: holds common data for both patient and doctor."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    user_type = Column(Enum(UserTypeEnum), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    patient = relationship("Patient", uselist=False, back_populates="user")
    doctor = relationship("Doctor", uselist=False, back_populates="user")
    notifications = relationship("Notification", back_populates="user")

# --- Patient model ---
class Patient(Base):
    """Patient: Extends User with patient-related data."""
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")

# --- Doctor model ---
class Doctor(Base):
    """Doctor: Extends User with doctor-related data."""
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialization = Column(String(255), nullable=True)
    about = Column(Text, nullable=True)

    user = relationship("User", back_populates="doctor")
    timeslots = relationship("TimeSlot", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

# --- TimeSlot model ---
class TimeSlot(Base):
    """TimeSlot: doctors specify available time slots."""
    __tablename__ = "timeslots"
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)

    doctor = relationship("Doctor", back_populates="timeslots")
    appointment = relationship("Appointment", back_populates="timeslot", uselist=False)

# --- Appointment model ---
class Appointment(Base):
    """Appointment: links a patient, doctor, and a timeslot."""
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    timeslot_id = Column(Integer, ForeignKey("timeslots.id"), nullable=False)
    status = Column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.PENDING, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    timeslot = relationship("TimeSlot", back_populates="appointment")
    notifications = relationship("Notification", back_populates="appointment")

# --- Notification model ---
class Notification(Base):
    """Notification: appointment status updates, general notifications."""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    type = Column(Enum(NotificationTypeEnum), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="notifications")
    appointment = relationship("Appointment", back_populates="notifications")
