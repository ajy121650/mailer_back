# user/models.py

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet, InvalidToken

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


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, password, **extra_fields)


# Django의 인증 시스템과 통합하기 위해 AbstractBaseUser와 PermissionsMixin을 상속받습니다.
class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True, verbose_name="사용자 아이디")
    is_staff = models.BooleanField(default=False, verbose_name="관리자 권한")
    is_active = models.BooleanField(default=True, verbose_name="활성 상태")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="가입일")

    objects = UserManager()

    USERNAME_FIELD = "username"  # 로그인 시 사용할 필드

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"

    def __str__(self):
        return self.username


class EmailAccount(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_accounts",
        verbose_name="사용자",
    )
    email_address = models.EmailField(unique=True, verbose_name="이메일 주소")
    # 암호화된 비밀번호를 저장합니다. 길이를 예측할 수 없으므로 TextField를 사용합니다.
    encrypted_password = models.TextField(verbose_name="암호화된 이메일 비밀번호", blank=True)
    priority = models.IntegerField(null=True, blank=True, verbose_name="우선순위")
    is_valid = models.BooleanField(default=True, verbose_name="유효 계정")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    @property
    def email_password(self):
        """암호화된 비밀번호를 복호화하여 반환합니다."""
        if not fernet or not self.encrypted_password:
            return ""
        try:
            # DB에서 읽어온 문자열을 다시 바이트로 인코딩하여 복호화합니다.
            decrypted_bytes = fernet.decrypt(self.encrypted_password.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            # 복호화에 실패하면 에러를 명확히 알리는 것이 좋습니다.
            return "DECRYPTION_FAILED"

    @email_password.setter
    def email_password(self, raw_password: str):
        """평문 비밀번호를 암호화하여 저장합니다."""
        if fernet and raw_password:
            # 평문 비밀번호를 바이트로 인코딩하여 암호화하고,
            # 저장하기 위해 다시 문자열로 디코딩합니다.
            self.encrypted_password = fernet.encrypt(raw_password.encode()).decode()
        else:
            self.encrypted_password = ""

    class Meta:
        verbose_name = "사용자 이메일 계정"
        verbose_name_plural = "사용자 이메일 계정 목록"
        ordering = ["user", "priority"]

    def __str__(self):
        return f"{self.user.username} - {self.email_address}"


class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="templates", verbose_name="작성자")
    template_content = models.TextField(verbose_name="템플릿 내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "템플릿"
        verbose_name_plural = "템플릿 목록"

    def __str__(self):
        return f"Template by {self.user.username} (ID: {self.id})"
