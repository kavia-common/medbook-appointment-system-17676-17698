"""Pydantic schemas for API input/output for appointment booking system."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# Enums (for schema use, keep synced with models.py)
class UserTypeEnum(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"

class AppointmentStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class NotificationTypeEnum(str, Enum):
    APPOINTMENT_REQUEST = "appointment_request"
    APPOINTMENT_UPDATE = "appointment_update"
    GENERAL = "general"

# --- User ---
# PUBLIC_INTERFACE
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email")
    full_name: str = Field(..., description="Full name")
    user_type: UserTypeEnum = Field(..., description="User type: patient or doctor")
    is_active: bool = Field(default=True, description="Is the user active")

# PUBLIC_INTERFACE
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password")

# PUBLIC_INTERFACE
class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True

# --- Patient ---
# PUBLIC_INTERFACE
class PatientBase(BaseModel):
    pass  # Placeholder for additional fields

# PUBLIC_INTERFACE
class PatientCreate(PatientBase):
    user: UserCreate

# PUBLIC_INTERFACE
class PatientRead(PatientBase):
    id: int
    user: UserRead

    class Config:
        orm_mode = True

# --- Doctor ---
# PUBLIC_INTERFACE
class DoctorBase(BaseModel):
    specialization: Optional[str] = Field(None, description="Doctor's specialization")
    about: Optional[str] = Field(None, description="About the doctor")

# PUBLIC_INTERFACE
class DoctorCreate(DoctorBase):
    user: UserCreate

# PUBLIC_INTERFACE
class DoctorRead(DoctorBase):
    id: int
    user: UserRead

    class Config:
        orm_mode = True

# --- TimeSlot ---
# PUBLIC_INTERFACE
class TimeSlotBase(BaseModel):
    start_time: datetime
    end_time: datetime

# PUBLIC_INTERFACE
class TimeSlotCreate(TimeSlotBase):
    pass

# PUBLIC_INTERFACE
class TimeSlotRead(TimeSlotBase):
    id: int
    is_booked: bool

    class Config:
        orm_mode = True

# --- Appointment ---
# PUBLIC_INTERFACE
class AppointmentBase(BaseModel):
    note: Optional[str] = Field(None, description="Optional note for the appointment")

# PUBLIC_INTERFACE
class AppointmentCreate(AppointmentBase):
    patient_id: int
    doctor_id: int
    timeslot_id: int

# PUBLIC_INTERFACE
class AppointmentRead(AppointmentBase):
    id: int
    patient_id: int
    doctor_id: int
    timeslot_id: int
    status: AppointmentStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# --- Notification ---
# PUBLIC_INTERFACE
class NotificationBase(BaseModel):
    type: NotificationTypeEnum
    message: str

# PUBLIC_INTERFACE
class NotificationCreate(NotificationBase):
    user_id: int
    appointment_id: Optional[int] = None

# PUBLIC_INTERFACE
class NotificationRead(NotificationBase):
    id: int
    user_id: int
    appointment_id: Optional[int]
    created_at: datetime
    is_read: bool

    class Config:
        orm_mode = True
