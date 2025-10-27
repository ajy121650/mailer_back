from django.db import models
from user.models import User
from email_account.utils import fernet
from cryptography.fernet import InvalidToken

# 각 이메일 어카운트 연동 시 프로필 설정해서 DB에 저장하는 view 필요.


# Create your models here.
class EmailAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_accounts")
    is_valid = models.BooleanField(default=True)
    domain = models.CharField(max_length=255)
    address = models.EmailField(unique=True)
    encrypted_password = models.CharField(max_length=255)

    #### 스팸 필터링을 위한 사용자 선호도 필드 ####
    interests = models.JSONField(
        null=True, blank=True, default=list, help_text="사용자 관심사 목록 (예: ['기술', '스포츠'])"
    )
    job = models.CharField(max_length=100, null=True, blank=True, help_text="사용자의 직업")
    usage = models.CharField(max_length=100, null=True, blank=True, help_text="계정의 용도 (예: 개인용, 업무용)")

    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def email_password(self):
        """암호화된 비밀번호를 복호화하여 반환합니다."""
        if not fernet or not self.encrypted_password:
            return ""
        try:
            decrypted_bytes = fernet.decrypt(self.encrypted_password.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            return "DECRYPTION_FAILED"

    @email_password.setter
    def email_password(self, raw_password: str):
        """평문 비밀번호를 암호화하여 저장합니다."""
        if fernet and raw_password:
            self.encrypted_password = fernet.encrypt(raw_password.encode()).decode()
        else:
            self.encrypted_password = ""

    def __str__(self):
        return self.address


# move folder if you want to
class SpamedMail(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="spamed_mails")
    address = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["account", "address"], name="uniq_spamed_email_per_account"),
        ]
