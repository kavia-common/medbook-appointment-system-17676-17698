"""Notification API endpoints for user notifications (list, read)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.api import models, schemas, database
from src.api.auth import get_current_user

router = APIRouter(
    prefix="/notification",
    tags=["Notification"],
)

# PUBLIC_INTERFACE
@router.get(
    "/mine",
    response_model=List[schemas.NotificationRead],
    summary="List my notifications",
    description="Returns a list of notifications for the current user (appointment requests, status updates, general). Sorted by newest first."
)
def list_my_notifications(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return list of notifications for the current user, sorted by creation time descending."""
    notifications = db.query(models.Notification)\
        .filter(models.Notification.user_id == current_user.id)\
        .order_by(models.Notification.created_at.desc())\
        .all()
    return [
        schemas.NotificationRead(
            id=n.id,
            user_id=n.user_id,
            appointment_id=n.appointment_id,
            type=n.type,
            message=n.message,
            created_at=n.created_at,
            is_read=n.is_read
        )
        for n in notifications
    ]

# PUBLIC_INTERFACE
@router.get(
    "/{notification_id}",
    response_model=schemas.NotificationRead,
    summary="Get notification by ID",
    description="Returns a notification by ID (only if it belongs to the current user)."
)
def get_notification_by_id(
    notification_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the details of a notification if it belongs to the current user."""
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return schemas.NotificationRead(
        id=notif.id,
        user_id=notif.user_id,
        appointment_id=notif.appointment_id,
        type=notif.type,
        message=notif.message,
        created_at=notif.created_at,
        is_read=notif.is_read
    )

# PUBLIC_INTERFACE
@router.patch(
    "/{notification_id}/read",
    response_model=schemas.NotificationRead,
    summary="Mark notification as read",
    description="Marks a notification as read by ID if owned by the current user."
)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return schemas.NotificationRead(
        id=notif.id,
        user_id=notif.user_id,
        appointment_id=notif.appointment_id,
        type=notif.type,
        message=notif.message,
        created_at=notif.created_at,
        is_read=notif.is_read
    )
