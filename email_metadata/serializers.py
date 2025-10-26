from rest_framework import serializers
from email_content.models import EmailContent
from .models import EmailMetadata



# 목록 조회를 위해 이메일 본문 미리보기를 하는 시리얼라이저.
class EmailPreviewSerializer(serializers.ModelSerializer):
    preview = serializers.SerializerMethodField()

    class Meta:
        model = EmailContent
        fields = [
            "subject",
            "from_header",
            "date",
            "preview",  # 본문 대신 미리보기 필드 preview 사용.
        ]

    def get_preview(self, obj):
        "본문 내용의 앞 100자를 잘라 미리보기를 생성."
        if obj.text_body:
            return obj.text_body[:100]
        return ""

# 간단한 목록 조회용 시리얼라이저
class EmailMetadataListSerializer(serializers.ModelSerializer):
    email = EmailPreviewSerializer(read_only=True)  # 위에서 만든 preview버전 사용.
    account_address = serializers.CharField(source="account.address", read_only=True)

    class Meta:
        model = EmailMetadata
        fields = [
            "id",
            "account_address",
            "folder",
            "is_read",
            "is_important",
            "is_pinned",
            "received_at",
            "email",  # 가벼운 EmailPreviewSerializer를 사용
        ]

######################################################################

# 상세 조회 및 수정용 시리얼라이저
class EmailContentSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailContent
        fields = [
            "subject",
            "from_header",
            "to_header",
            "cc_header",
            "bcc_header",
            "text_body",
            "html_body",
            "date",
        ]

# 메일 세부정보 조회를 위한 시리얼라이저
class EmailDetailSerializer(serializers.ModelSerializer):

    email = EmailContentSerializer(read_only=True)
    account_address = serializers.CharField(source="account.address", read_only=True)

    class Meta:
        model = EmailMetadata
        fields = [
            "id",
            "account_address",
            "folder",
            "is_read",
            "is_important",
            "is_pinned",
            "received_at",
            "email",
        ]

######################################################################

# 메일 메타데이터의 수정을 위한 시리얼라이저.
class EmailUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailMetadata
        fields = [
            "folder",
            "is_read",
            "is_important",
            "is_pinned",
        ]
        extra_kwargs = {
            "folder": {"required": False},
            "is_read": {"required": False},
            "is_important": {"required": False},
            "is_pinned": {"required": False},
        }