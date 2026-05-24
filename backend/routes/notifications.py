from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime, timedelta
from database import get_db, Base
from services.datetime_utils import utc_now_naive
from services.lifecycle import NotificationType
from models.user import User, UserRole
from schemas.notifications import NotificationListResponse
from services.rbac import AuthPrincipal, ExecutionLane, load_principal_user, require_role, require_roles

router = APIRouter(prefix="/notifications", tags=["notifications"])
AUTHENTICATED_ACCESS = require_roles(UserRole.CUSTOMER, UserRole.DRIVER, UserRole.ADMIN)
ADMIN_ACCESS = require_role("admin")

# Notification Model
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (CheckConstraint("is_read IN (0, 1)", name="ck_notifications_is_read_bool"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # Target user (None for broadcast)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default=NotificationType.SYSTEM.value)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    expires_at = Column(DateTime, nullable=True)

# Pydantic models
class NotificationCreate(BaseModel):
    title: str
    message: str
    type: NotificationType = NotificationType.SYSTEM
    user_id: int = None  # None for broadcast
    expires_hours: int = 24  # Auto-expire after 24 hours

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

@router.get("/")
def get_notifications(
    user: AuthPrincipal = Depends(AUTHENTICATED_ACCESS),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """Get notifications for the current user"""
    user = load_principal_user(db, user)
    # Get user-specific notifications and broadcast notifications
    notifications = db.query(Notification).filter(
        (Notification.user_id == user.id) | (Notification.user_id == None),
        (Notification.expires_at == None) | (Notification.expires_at > utc_now_naive())
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    unread_count = len([n for n in notifications if not n.is_read])
    
    return {
        "notifications": [{
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "read": n.is_read,
            "created_at": n.created_at
        } for n in notifications],
        "unread_count": unread_count
    }

@router.post("/send")
def send_notification(
    payload: NotificationCreate, 
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), 
    db: Session = Depends(get_db)
):
    """Send notification (admin only)"""
    load_principal_user(db, admin_user)
    expires_at = utc_now_naive() + timedelta(hours=payload.expires_hours)
    
    notification = Notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        type=payload.type.value,
        expires_at=expires_at
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # Count recipients
    if payload.user_id:
        recipient_count = 1
        recipient_type = "specific user"
    else:
        recipient_count = db.query(User).filter(User.is_active.is_(True)).count()
        recipient_type = "all active users"
    
    return {
        "message": f"Notification sent successfully",
        "notification_id": notification.id,
        "recipients": f"{recipient_count} {recipient_type}",
        "expires_at": expires_at
    }

@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    user: AuthPrincipal = Depends(AUTHENTICATED_ACCESS),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    user = load_principal_user(db, user)
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        (Notification.user_id == user.id) | (Notification.user_id == None)
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db)
):
    """Delete a notification (admin only)"""
    load_principal_user(db, admin_user)
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted successfully"}

# Driver-specific notification endpoints
@router.post("/driver/ride-alert")
def send_ride_alert(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    """Send ride availability alert to all active drivers"""
    load_principal_user(db, admin_user)
    from services.driver_approval import query_dispatch_available_driver_ids

    available_ids = set(query_dispatch_available_driver_ids(db))
    if not available_ids:
        active_drivers = []
    else:
        active_drivers = (
            db.query(User)
            .filter(
                User.role == UserRole.DRIVER,
                User.is_active.is_(True),
                User.id.in_(available_ids),
            )
            .all()
        )
    
    notifications_sent = 0
    for driver in active_drivers:
        notification = Notification(
            user_id=driver.id,
            title="🚗 New Ride Available",
            message="A new ride request is available in your area. Check the app to accept!",
            type=NotificationType.RIDE_REQUESTED.value,
            expires_at=utc_now_naive() + timedelta(hours=1)
        )
        db.add(notification)
        notifications_sent += 1
    
    db.commit()
    
    return {
        "message": f"Ride alerts sent to {notifications_sent} active drivers",
        "recipients": notifications_sent
    }