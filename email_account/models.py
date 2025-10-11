from django.db import models
from user.models import User
from email_account.utils import fernet
from cryptography.fernet import InvalidToken


# Create your models here.
class EmailAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_accounts")
    priority = models.PositiveSmallIntegerField(default=1)  # (user, priority) 유니크 권장
    is_valid = models.BooleanField(default=True)
    domain = models.CharField(max_length=255)
    address = models.EmailField(unique=True)
    encrypted_password = models.CharField(max_length=255)
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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "priority"], name="uniq_user_priority"),
        ]

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
