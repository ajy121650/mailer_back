from django.db import models
from email_account.models import EmailAccount
from email_content.models import EmailContent as Emails


# Create your models here.
class EmailMetadata(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="metadata")
    email = models.ForeignKey(Emails, on_delete=models.CASCADE, related_name="metadata")
    uid = models.CharField(max_length=255)  # 이메일 서버에서 주는 고유 ID

    FOLDER_CHOICES = [
        ("inbox", "Inbox"),
        ("sent", "Sent"),
        ("junk", "Junk"),
        ("starred", "Starred"),
    ]
    folder = models.CharField(max_length=20, choices=FOLDER_CHOICES, default="inbox")

    is_important = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_summarized = models.BooleanField(default=False)
    summarized_content = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # null이면 삭제 안된 상태

    class Meta:
        constraints = [
            # ✅ 같은 계정에 같은 이메일 중복 방지
            models.UniqueConstraint(fields=["account", "email"], name="uniq_account_email"),
        ]
