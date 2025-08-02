"""Endpoints for listing and searching doctors."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.api import models, schemas, database

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor"],
)

# PUBLIC_INTERFACE
@router.get("/", response_model=List[schemas.DoctorRead], summary="List all doctors", description="Return a list of all doctors. Supports optional search by specialization or name.")
def list_doctors(
    db: Session = Depends(database.get_db),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    name: Optional[str] = Query(None, description="Search by doctor name")
):
    """
    List all doctors, with optional search by specialization and/or doctor full name.
    """
    query = db.query(models.Doctor).join(models.User)
    if specialization:
        query = query.filter(models.Doctor.specialization.ilike(f"%{specialization}%"))
    if name:
        query = query.filter(models.User.full_name.ilike(f"%{name}%"))
    doctors = query.all()
    result = []
    for doc in doctors:
        result.append(
            schemas.DoctorRead(
                id=doc.id,
                user=doc.user,
                specialization=doc.specialization,
                about=doc.about
            )
        )
    return result

# PUBLIC_INTERFACE
@router.get("/{doctor_id}", response_model=schemas.DoctorRead, summary="Get doctor by ID", description="Fetch a specific doctor profile by doctor ID")
def get_doctor_by_id(
    doctor_id: int,
    db: Session = Depends(database.get_db)
):
    """Fetch a doctor by doctor ID."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Doctor not found")
    return schemas.DoctorRead(
        id=doctor.id,
        user=doctor.user,
        specialization=doctor.specialization,
        about=doctor.about
    )
