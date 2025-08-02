"""User and profile management endpoints for appointment booking system."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api import models, schemas, database
from src.api.auth import get_current_user

router = APIRouter(
    prefix="/user",
    tags=["User and Profile"],
)

# PUBLIC_INTERFACE
@router.get("/me", response_model=schemas.UserRead, summary="Get my user info", description="Fetch user details for the currently authenticated user.")
def get_my_user_info(current_user: models.User = Depends(get_current_user)):
    """Get info about the currently authenticated user."""
    return schemas.UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        user_type=current_user.user_type,
        is_active=current_user.is_active
    )

# PUBLIC_INTERFACE
@router.get("/me/profile", summary="Get current user's profile", response_model=schemas.PatientRead | schemas.DoctorRead)
def get_my_profile(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Returns full patient or doctor profile for the authenticated user."""
    if current_user.user_type == models.UserTypeEnum.PATIENT:
        patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        return schemas.PatientRead(id=patient.id, user=current_user)
    elif current_user.user_type == models.UserTypeEnum.DOCTOR:
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        return schemas.DoctorRead(
            id=doctor.id,
            user=current_user,
            specialization=doctor.specialization,
            about=doctor.about
        )
    raise HTTPException(status_code=400, detail="Unknown user type")

# PUBLIC_INTERFACE
@router.patch("/me/profile", summary="Patch/Edit current user's profile", response_model=schemas.PatientRead | schemas.DoctorRead)
def update_my_profile(
    profile_update: dict,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update fields for the authenticated user's profile.
    Patients: Can update full_name, email.
    Doctors: Can update full_name, email, specialization, about.
    """
    allowed_user_fields = {"full_name", "email"}
    
    # Only update allowed User fields
    user_data = {k: v for k, v in profile_update.items() if k in allowed_user_fields}
    if user_data:
        for k, v in user_data.items():
            setattr(current_user, k, v)
        db.add(current_user)
        db.commit()
        db.refresh(current_user)

    if current_user.user_type == models.UserTypeEnum.PATIENT:
        patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
        # For patient, only User fields are editable
        result = schemas.PatientRead(id=patient.id, user=current_user)
    elif current_user.user_type == models.UserTypeEnum.DOCTOR:
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        doctor_data = {}
        for fld in ["specialization", "about"]:
            if fld in profile_update:
                setattr(doctor, fld, profile_update[fld])
                doctor_data[fld] = profile_update[fld]
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        result = schemas.DoctorRead(
            id=doctor.id,
            user=current_user,
            specialization=doctor.specialization,
            about=doctor.about
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown user type")
    return result

# PUBLIC_INTERFACE
@router.get("/{user_id}/type", summary="Detect user type", description="Fetch whether a user ID is a patient or doctor", response_model=schemas.UserTypeEnum)
def get_user_type(
    user_id: int,
    db: Session = Depends(database.get_db)
):
    """Return the user type for a given user id."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.user_type

# PUBLIC_INTERFACE
@router.get("/{user_id}/profile", summary="Fetch any user's profile", response_model=schemas.PatientRead | schemas.DoctorRead)
def get_profile_by_user_id(
    user_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Fetch a profile (patient/doctor) for a given user id.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_type == models.UserTypeEnum.PATIENT:
        patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        return schemas.PatientRead(id=patient.id, user=user)
    elif user.user_type == models.UserTypeEnum.DOCTOR:
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        return schemas.DoctorRead(
            id=doctor.id,
            user=user,
            specialization=doctor.specialization,
            about=doctor.about
        )
    raise HTTPException(status_code=400, detail="Unknown user type")

# PUBLIC_INTERFACE
@router.delete("/me", summary="Delete my user account", status_code=204)
def delete_my_account(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete (disable) current user. All related data stays by default, but user becomes inactive."""
    current_user.is_active = False
    db.add(current_user)
    db.commit()
    return None
