# email/models.py

from django.db import models


# 이메일 내용에 대한 모델
class Email(models.Model):
    subject = models.CharField(max_length=255, blank=True, null=True, verbose_name="제목")
    body = models.TextField(blank=True, null=True, verbose_name="본문")
    from_address = models.EmailField(verbose_name="보낸 사람")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="보낸 시각")

    class Meta:
        verbose_name = "이메일"
        verbose_name_plural = "이메일 목록"

    def __str__(self):
        return self.subject or f"Email from {self.from_address}"


class EmailRecipient(models.Model):
    class RecipientType(models.TextChoices):
        TO = "TO", "받는 사람"
        CC = "CC", "참조"
        BCC = "BCC", "숨은 참조"

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name="이메일",
    )
    recipient_address = models.EmailField(verbose_name="수신 주소")
    recipient_type = models.CharField(max_length=3, choices=RecipientType.choices, verbose_name="수신자 유형")

    class Meta:
        verbose_name = "이메일 수신자"
        verbose_name_plural = "이메일 수신자 목록"

    def __str__(self):
        return f"[{self.recipient_type}] {self.recipient_address} for Email ID {self.email_id}"


# 메일함 모델: 이메일과 이메일 계정을 연결하고, 폴더 및 상태 정보를 관리.
class Mailbox(models.Model):
    class FolderType(models.TextChoices):
        INBOX = "inbox", "받은 메일함"
        JUNK = "junk", "스팸 메일함"
        DRAFTS = "drafts", "임시보관함"
        SENT = "sent", "보낸 메일함"
        ARCHIVE = "archive", "보관함"
        DELETED = "deleted", "휴지통"

    account = models.ForeignKey(
        "user.EmailAccount",
        on_delete=models.CASCADE,
        related_name="mailbox_items",
        verbose_name="이메일 계정",
    )
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="mailbox_entries",
        verbose_name="이메일",
    )
    folder = models.CharField(
        max_length=50,
        choices=FolderType.choices,
        default=FolderType.INBOX,
        verbose_name="폴더",
    )
    is_important = models.BooleanField(default=False, verbose_name="중요 표시")
    is_pinned = models.BooleanField(default=False, verbose_name="고정")
    is_read = models.BooleanField(default=False, verbose_name="읽음 여부")
    is_summarized = models.BooleanField(default=False, verbose_name="요약 여부")
    summarized_content = models.TextField(blank=True, null=True, verbose_name="요약된 내용")
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="수신 시각")

    class Meta:
        verbose_name = "메일함"
        verbose_name_plural = "메일함 목록"
        # 한 계정은 동일한 이메일을 한 번만 가질 수 있도록 제약
        unique_together = ("account", "email")

    def __str__(self):
        return f"{self.account.email_address} - {self.email.subject}"


class Attachment(models.Model):
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="이메일",
    )
    # FileField는 파일 업로드와 경로 관리를 편리하게 해줍니다.
    file = models.FileField(upload_to="attachments/%Y/%m/%d/", verbose_name="첨부 파일")
    file_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="파일 이름")
    file_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="파일 타입")
    file_size = models.BigIntegerField(blank=True, null=True, verbose_name="파일 크기")

    class Meta:
        verbose_name = "첨부파일"
        verbose_name_plural = "첨부파일 목록"

    def __str__(self):
        return self.file_name or f"Attachment for Email ID {self.email_id}"
