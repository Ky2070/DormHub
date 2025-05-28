import os
import django
# Khởi tạo Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dormapis.settings')
django.setup()
from pathlib import Path
from django.utils import timezone
from django.utils.timezone import localtime
import pytz
from dormapis.settings import BASE_DIR
# Phòng thí nghiệm dùng để test các trường hợp xử lý,...
BASE_DIR = Path(__file__).resolve().parent.parent
FIREBASE_CREDENTIAL_PATH = BASE_DIR / 'firebase' / 'dormapp-11c0b-firebase-adminsdk-fbsvc-a17d1982ce.json'
print(FIREBASE_CREDENTIAL_PATH)
# Lấy thời gian hiện tại theo UTC
utc_now = timezone.now()

# Dùng localtime nếu settings.py đã set TIME_ZONE = 'Asia/Ho_Chi_Minh'
local_now = localtime(utc_now)

print("UTC now:           ", utc_now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))
print("Localtime (Django):", local_now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))