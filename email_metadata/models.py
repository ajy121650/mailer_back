from django.db import models
from email_account.models import EmailAccount
from email_content.models import EmailContent as Emails


# Create your models here.
class EmailMetadata(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="metadata")
    email = models.ForeignKey(Emails, on_delete=models.CASCADE, related_name="metadata")
    uid = models.CharField(max_length=255)  # 이메일 서버에서 주는 고유 ID

    FOLDER_CHOICES = [
        ("inbox", "받은 편지함"),
        ("sent", "보낸 편지함"),
        ("spam", "스팸 편지함"),
        ("starred", "별표 편지함"),
        ("trash", "휴지통"),
    ]
    folder = models.CharField(
        max_length=20,
        choices=FOLDER_CHOICES,
        default="inbox",
        help_text="폴더 지정: inbox(받은 편지함), sent(보낸 편지함), spam(스팸 메일함), starred(별표 편지함), trash(휴지통)",
    )

    is_important = models.BooleanField(default=False, help_text="중요 메일 표시 여부")
    is_pinned = models.BooleanField(default=False, help_text="상단 고정 여부")
    is_read = models.BooleanField(default=False, help_text="읽음 상태 여부")
    is_summarized = models.BooleanField(default=False, help_text="요약 여부")
    is_spammed = models.BooleanField(default=False, help_text="스팸 메일 여부")
    summarized_content = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # null이면 삭제 안된 상태

    class Meta:
        constraints = [
            # ✅ 같은 계정에 같은 이메일 중복 방지
            models.UniqueConstraint(fields=["account", "email"], name="uniq_account_email"),
        ]
