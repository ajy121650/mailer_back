from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet

# Initialize Fernet with the key from settings
key = getattr(settings, "FERNET_KEY", None)
if not key:
    raise ImproperlyConfigured("FERNET_KEY가 .env 파일에 설정되지 않았습니다. 먼저 키를 생성하고 설정해주세요.")

try:
    # The key from settings (read from .env) will be a string.
    # Fernet requires bytes.
    fernet = Fernet(key.encode())
except (ValueError, TypeError) as e:
    raise ImproperlyConfigured(
        f"FERNET_KEY가 유효하지 않습니다. URL-safe base64-encoded 32-byte 키여야 합니다. 상세 정보: {e}"
    )
