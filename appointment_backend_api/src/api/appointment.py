"""Appointment endpoints for patients to book, doctors to confirm/reject, and users to view appointments."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from src.api import models, schemas, database
from src.api.auth import get_current_user

router = APIRouter(
    prefix="/appointment",
    tags=["Appointment"],
)

def get_current_patient(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
) -> models.Patient:
    """Return patient ORM object for current user, raises 403/404 if not patient."""
    if current_user.user_type != models.UserTypeEnum.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can perform this action")
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient

def get_current_doctor(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
) -> models.Doctor:
    """Return doctor ORM object for current user, raises 403/404 if not doctor."""
    if current_user.user_type != models.UserTypeEnum.DOCTOR:
        raise HTTPException(status_code=403, detail="Only doctors can perform this action")
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor

# PUBLIC_INTERFACE
@router.post(
    "/", 
    response_model=schemas.AppointmentRead,
    status_code=201,
    summary="Patient books an appointment slot",
    description="Patient books an available time slot with a doctor. Returns created appointment."
)
def book_appointment(
    payload: schemas.AppointmentCreate,
    db: Session = Depends(database.get_db),
    patient: models.Patient = Depends(get_current_patient),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allow patients to book an available time slot with a doctor.
    Ensures patient only books as themselves and slot is available.
    """
    # Ensure patient is booking for themselves only
    if payload.patient_id != patient.id:
        raise HTTPException(status_code=400, detail="patient_id mismatch (must use your own)")
    
    # Validate doctor exists
    doctor = db.query(models.Doctor).filter(models.Doctor.id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor not found")

    # Check timeslot exists and is not booked, and is for correct doctor
    timeslot = db.query(models.TimeSlot).filter(models.TimeSlot.id == payload.timeslot_id).first()
    if not timeslot or timeslot.is_booked or timeslot.doctor_id != doctor.id:
        raise HTTPException(status_code=400, detail="Time slot unavailable or not for given doctor")

    # Create appointment
    now = datetime.utcnow()
    appt = models.Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        timeslot_id=timeslot.id,
        note=payload.note,
        status=models.AppointmentStatusEnum.PENDING,
        created_at=now,
        updated_at=None,
    )
    # Book slot
    timeslot.is_booked = True
    db.add(appt)
    db.commit()
    db.refresh(appt)
    db.refresh(timeslot)

    # --- Trigger notification for doctor (appointment request) ---
    # Notification to doctor for new appointment request
    notif = models.Notification(
        user_id=doctor.user_id,
        appointment_id=appt.id,
        type=models.NotificationTypeEnum.APPOINTMENT_REQUEST,
        message=f"New appointment request from {patient.user.full_name}.",
        created_at=datetime.utcnow(),
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    return schemas.AppointmentRead(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        timeslot_id=appt.timeslot_id,
        note=appt.note,
        status=appt.status,
        created_at=appt.created_at,
        updated_at=appt.updated_at
    )

class AppointmentStatusChangeRequest(schemas.BaseModel):
    """Request body for confirming/rejecting appointment."""
    new_status: schemas.AppointmentStatusEnum = schemas.Field(
        ..., description="New status. Must be either 'confirmed' or 'rejected'."
    )
    note: Optional[str] = schemas.Field(
        None, description="Optional note/reason."
    )

    class Config:
        extra = "forbid"

# PUBLIC_INTERFACE
@router.patch(
    "/{appointment_id}/status",
    response_model=schemas.AppointmentRead,
    summary="Doctor confirm/reject appointment",
    description="Doctor confirms or rejects a pending appointment for their slot.",
)
def confirm_or_reject_appointment(
    appointment_id: int,
    status_req: AppointmentStatusChangeRequest,
    db: Session = Depends(database.get_db),
    doctor: models.Doctor = Depends(get_current_doctor),
):
    """
    Allows doctor to confirm or reject a pending appointment.
    Only the doctor assigned to this appointment may modify it. 
    """
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Cannot modify another doctor's appointment")
    if appt.status != models.AppointmentStatusEnum.PENDING:
        raise HTTPException(status_code=409, detail="Appointment is already handled")

    # Only allow 'confirmed' or 'rejected' transitions
    if status_req.new_status not in (models.AppointmentStatusEnum.CONFIRMED, models.AppointmentStatusEnum.REJECTED):
        raise HTTPException(status_code=400, detail="Invalid status update. Allowed: confirmed, rejected")

    appt.status = status_req.new_status
    appt.updated_at = datetime.utcnow()

    # Save optional note/reason for auditing
    if status_req.note:
        appt.note = status_req.note

    # If rejected, free the timeslot
    if appt.status == models.AppointmentStatusEnum.REJECTED:
        timeslot = db.query(models.TimeSlot).filter(models.TimeSlot.id == appt.timeslot_id).first()
        if timeslot:
            timeslot.is_booked = False
            db.add(timeslot)
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # --- Trigger notification for patient regarding status update ---
    notif_type = models.NotificationTypeEnum.APPOINTMENT_UPDATE
    if appt.status == models.AppointmentStatusEnum.CONFIRMED:
        message = f"Your appointment with Dr. {appt.doctor.user.full_name} has been confirmed."
    else:
        # REJECTED
        message = f"Your appointment with Dr. {appt.doctor.user.full_name} was rejected."
        if status_req.note:
            message += f" Reason: {status_req.note}"

    notif = models.Notification(
        user_id=appt.patient.user_id,
        appointment_id=appt.id,
        type=notif_type,
        message=message,
        created_at=datetime.utcnow(),
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    return schemas.AppointmentRead(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        timeslot_id=appt.timeslot_id,
        note=appt.note,
        status=appt.status,
        created_at=appt.created_at,
        updated_at=appt.updated_at
    )

# PUBLIC_INTERFACE
@router.get(
    "/mine",
    response_model=List[schemas.AppointmentRead],
    summary="Get my appointments",
    description="Returns list of all appointments for the current user (role-based, as patient or doctor)."
)
def list_my_appointments(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return list of appointments for the current user:
    - Patient: appointments where they are patient.
    - Doctor: appointments where they are doctor.
    """
    if current_user.user_type == models.UserTypeEnum.PATIENT:
        patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        appts = db.query(models.Appointment).filter(models.Appointment.patient_id == patient.id).all()
    elif current_user.user_type == models.UserTypeEnum.DOCTOR:
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor.id).all()
    else:
        raise HTTPException(status_code=403, detail="Unknown user type")

    return [
        schemas.AppointmentRead(
            id=a.id,
            patient_id=a.patient_id,
            doctor_id=a.doctor_id,
            timeslot_id=a.timeslot_id,
            note=a.note,
            status=a.status,
            created_at=a.created_at,
            updated_at=a.updated_at
        )
        for a in appts
    ]

# PUBLIC_INTERFACE
@router.get(
    "/{appointment_id}",
    response_model=schemas.AppointmentRead,
    summary="Get appointment by ID",
    description="Returns an appointment by ID (only if it belongs to the current user)."
)
def get_appointment_by_id(
    appointment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns appointment by ID if user is involved (as patient or doctor).
    """
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    # Permission: must be involved
    if current_user.user_type == models.UserTypeEnum.PATIENT:
        patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
        if not patient or appt.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Not your appointment")
    elif current_user.user_type == models.UserTypeEnum.DOCTOR:
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        if not doctor or appt.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Not your appointment")
    else:
        raise HTTPException(status_code=403, detail="Unknown user type")
    return schemas.AppointmentRead(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        timeslot_id=appt.timeslot_id,
        note=appt.note,
        status=appt.status,
        created_at=appt.created_at,
        updated_at=appt.updated_at
    )
