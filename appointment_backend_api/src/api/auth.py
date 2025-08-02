"""Authentication endpoints (register/login) and JWT utilities for appointment booking app."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr

from src.api import models, schemas, database

import os

# --- JWT configuration ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "supersecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Pydantic Models for login/response ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int
    user_type: str

# --- Password utility functions ---
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT utility functions ---
# PUBLIC_INTERFACE
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# PUBLIC_INTERFACE
def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode JWT and return token data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        user_type: str = payload.get("user_type")
        if user_id is None or user_type not in ("patient", "doctor"):
            return None
        return TokenData(user_id=user_id, user_type=user_type)
    except JWTError:
        return None

# --- Dependency for authentication ---
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# PUBLIC_INTERFACE
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    """Fetch the current user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(token)
    if not token_data:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user

# --- Registration endpoints ---

# PUBLIC_INTERFACE
@router.post("/register/patient", response_model=schemas.PatientRead, summary="Register new patient", description="Register a patient account and return patient info.")
def register_patient(payload: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new patient."""
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.user_type != "patient":
        raise HTTPException(status_code=400, detail="user_type must be 'patient' for this endpoint")

    hashed_pw = get_password_hash(payload.password)
    user = models.User(
        email=payload.email,
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        user_type=models.UserTypeEnum.PATIENT,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    patient = models.Patient(user_id=user.id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return schemas.PatientRead(id=patient.id, user=user)

# PUBLIC_INTERFACE
@router.post("/register/doctor", response_model=schemas.DoctorRead, summary="Register new doctor", description="Register a doctor account and return doctor info.")
def register_doctor(
    payload: schemas.UserCreate,
    specialization: Optional[str] = None,
    about: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """Register a new doctor."""
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.user_type != "doctor":
        raise HTTPException(status_code=400, detail="user_type must be 'doctor' for this endpoint")

    hashed_pw = get_password_hash(payload.password)
    user = models.User(
        email=payload.email,
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        user_type=models.UserTypeEnum.DOCTOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    doctor = models.Doctor(user_id=user.id, specialization=specialization, about=about)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return schemas.DoctorRead(id=doctor.id, user=user, specialization=specialization, about=about)

# --- Login endpoint ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# PUBLIC_INTERFACE
@router.post("/login", response_model=Token, summary="Login and get JWT", description="Login as patient or doctor and receive a JWT access token.")
def login(request: LoginRequest, db: Session = Depends(database.get_db)):
    """Authenticate user and provide JWT token."""
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    access_token = create_access_token(data={"sub": str(user.id), "user_type": user.user_type.value})
    return Token(access_token=access_token, token_type="bearer")
