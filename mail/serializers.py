from rest_framework import serializers
from .models import Mailbox, Email, EmailRecipient


class EmailRecipientSerializer(serializers.ModelSerializer):
    """이메일 수신자 정보를 위한 시리얼라이저"""

    class Meta:
        model = EmailRecipient
        fields = ["recipient_address", "recipient_type"]


class EmailSerializer(serializers.ModelSerializer):
    """Email 모델의 내용을 보여주기 위한 기본 시리얼라이저"""

    recipients = EmailRecipientSerializer(many=True, read_only=True)

    class Meta:
        model = Email
        fields = ["subject", "from_address", "sent_at", "body", "recipients"]


class MailboxSerializer(serializers.ModelSerializer):
    """메일 목록 조회를 위한 시리얼라이저"""

    # Mailbox 모델에 속한 email(ForeignKey)의 상세 정보를 보여주기 위해 EmailSerializer를 중첩하여 사용합니다.
    email = EmailSerializer(read_only=True)
    # Mailbox 모델에 속한 account(ForeignKey)에서 이메일 주소만 가져와서 보여줍니다.
    account_address = serializers.CharField(source="account.email_address", read_only=True)

    class Meta:
        model = Mailbox
        fields = [
            "id",
            "account_address",  # 어느 계정의 메일인지 표시
            "folder",
            "is_read",
            "is_important",
            "is_pinned",
            "received_at",
            "email",  # 이메일 상세 정보 (EmailSerializer를 통해 표시)
        ]
