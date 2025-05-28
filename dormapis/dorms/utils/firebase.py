import firebase_admin
from firebase_admin import credentials
import os
from pathlib import Path
# Đường dẫn tới file JSON
# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# FIREBASE_CREDENTIAL_PATH = os.path.join(BASE_DIR, 'firebase', 'dormapp-11c0b-firebase-adminsdk-fbsvc-a17d1982ce.json')
BASE_DIR = Path(__file__).resolve().parent.parent
FIREBASE_CREDENTIAL_PATH = BASE_DIR / 'firebase' / 'dormapp-11c0b-firebase-adminsdk-fbsvc-a17d1982ce.json'

if not os.path.exists(FIREBASE_CREDENTIAL_PATH):
    raise FileNotFoundError(f"Firebase credentials file not found at: {FIREBASE_CREDENTIAL_PATH}")
print("Firebase JSON path:", FIREBASE_CREDENTIAL_PATH)

# Khởi tạo Firebase app (chỉ chạy một lần)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIAL_PATH)
    firebase_admin.initialize_app(cred)