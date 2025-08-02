"""Endpoints for doctor time slot management (doctors: CRUD, patients: view available)."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime

from src.api import models, schemas, database
from src.api.auth import get_current_user

router = APIRouter(
    prefix="/timeslot",
    tags=["TimeSlot"],
)

def get_current_doctor(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.user_type != models.UserTypeEnum.DOCTOR:
        raise HTTPException(status_code=403, detail="Only accessible to doctor users")
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor

# PUBLIC_INTERFACE
@router.get("/available/{doctor_id}", response_model=List[schemas.TimeSlotRead], summary="List available time slots for doctor", description="Patients use this to see all available (not booked) future slots for a doctor.")
def list_available_timeslots(
    doctor_id: int,
    db: Session = Depends(database.get_db),
):
    """List all not-booked and future time slots for a doctor."""
    now = datetime.utcnow()
    slots = db.query(models.TimeSlot).filter(
        models.TimeSlot.doctor_id == doctor_id,
        models.TimeSlot.is_booked == False,
        models.TimeSlot.end_time > now
    ).all()
    return [
        schemas.TimeSlotRead(
            id=s.id,
            start_time=s.start_time,
            end_time=s.end_time,
            is_booked=s.is_booked
        ) for s in slots
    ]

# PUBLIC_INTERFACE
@router.get("/mine", response_model=List[schemas.TimeSlotRead], summary="List my time slots (doctor)", description="Doctors view all their own time slots (booked and unbooked).")
def list_my_timeslots(
    db: Session = Depends(database.get_db),
    doctor: models.Doctor = Depends(get_current_doctor)
):
    """Doctor: list all own slots (booked or not)."""
    slots = db.query(models.TimeSlot).filter(models.TimeSlot.doctor_id == doctor.id).all()
    return [
        schemas.TimeSlotRead(
            id=s.id,
            start_time=s.start_time,
            end_time=s.end_time,
            is_booked=s.is_booked
        ) for s in slots
    ]

# PUBLIC_INTERFACE
@router.post("/", response_model=schemas.TimeSlotRead, status_code=201, summary="Create a new time slot (doctor)", description="Doctor adds a new available time slot.")
def create_timeslot(
    slot: schemas.TimeSlotCreate,
    db: Session = Depends(database.get_db),
    doctor: models.Doctor = Depends(get_current_doctor)
):
    """Add a new open slot as doctor."""
    if slot.start_time >= slot.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    new_slot = models.TimeSlot(
        doctor_id=doctor.id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        is_booked=False
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return schemas.TimeSlotRead(
        id=new_slot.id,
        start_time=new_slot.start_time,
        end_time=new_slot.end_time,
        is_booked=new_slot.is_booked
    )

# PUBLIC_INTERFACE
@router.delete("/{slot_id}", status_code=204, summary="Delete a time slot (doctor)", description="Doctor deletes one of their own time slots (slot must not be booked).")
def delete_timeslot(
    slot_id: int,
    db: Session = Depends(database.get_db),
    doctor: models.Doctor = Depends(get_current_doctor)
):
    """Delete a slot if it belongs to this doctor and is not booked."""
    slot = db.query(models.TimeSlot).filter(models.TimeSlot.id == slot_id, models.TimeSlot.doctor_id == doctor.id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Cannot delete a slot that has already been booked")
    db.delete(slot)
    db.commit()
    return None

# PUBLIC_INTERFACE
@router.patch("/{slot_id}", response_model=schemas.TimeSlotRead, summary="Update a time slot (doctor)", description="Doctor updates start/end time for their own slot (must not be booked).")
def update_timeslot(
    slot_id: int,
    slot_update: schemas.TimeSlotCreate,
    db: Session = Depends(database.get_db),
    doctor: models.Doctor = Depends(get_current_doctor)
):
    """Update a slot's start/end if doctor owns it and it's not booked."""
    slot = db.query(models.TimeSlot).filter(models.TimeSlot.id == slot_id, models.TimeSlot.doctor_id == doctor.id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Cannot modify a slot that has been booked")
    if slot_update.start_time >= slot_update.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    slot.start_time = slot_update.start_time
    slot.end_time = slot_update.end_time
    db.commit()
    db.refresh(slot)
    return schemas.TimeSlotRead(
        id=slot.id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        is_booked=slot.is_booked
    )
