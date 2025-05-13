from firebase_admin import messaging
from ..utils.firebase import *


def send_push_notification(token: str, title: str, body: str, data: dict = None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token,
        data=data or {}
    )

    try:
        response = messaging.send(message)
        print("✅ Push notification sent:", response)
        return response
    except Exception as e:
        print("❌ Failed to send push notification:", e)
        return None

