import firebase_admin
from firebase_admin import credentials
import os

# Đường dẫn tới file JSON
FIREBASE_CREDENTIAL_PATH = os.path.join(
    os.path.dirname(__file__),
    'dormapp-11c0b-firebase-adminsdk-fbsvc-a17d1982ce.json'
)

# Khởi tạo Firebase app (chỉ chạy một lần)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIAL_PATH)
    firebase_admin.initialize_app(cred)