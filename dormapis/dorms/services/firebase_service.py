from firebase_admin import messaging
from ..utils.firebase import *
from ..models import FCMDevice


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
    except messaging.UnregisteredError:
        # Token không hợp lệ (user gỡ cài app chẳng hạn)
        print(f"⚠️ Token không còn hợp lệ: {token}")
        # Optional: Có thể xóa token này khỏi DB ở đây nếu muốn
        return False
    except Exception as e:
        print("❌ Failed to send push notification:", e)
        return None


def notify_user(user, title: str, body: str, data: dict = None):
    devices = FCMDevice.objects.filter(user=user)
    for device in devices:
        send_push_notification(
            token=device.token,
            title=title,
            body=body,
            data=data or {}
        )