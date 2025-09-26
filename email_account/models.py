from django.db import models
from user.models import User


# Create your models here.
class EmailAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_accounts")
    priority = models.PositiveSmallIntegerField(default=1)  # (user, priority) 유니크 권장
    is_valid = models.BooleanField(default=True)
    domain = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    encrypted_password = models.CharField(max_length=255)
    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "priority"], name="uniq_user_priority"),
        ]

    def __str__(self):
        return self.email


# move folder if you want to
class SpamedMail(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="spamed_mails")
    address = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["account", "address"], name="uniq_spamed_email_per_account"),
        ]
