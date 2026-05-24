from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from services.lifecycle import NotificationType


class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    type: NotificationType
    title: str
    message: str
    read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
