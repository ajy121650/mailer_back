from rest_framework import serializers
from email_content.models import EmailContent
from .models import EmailMetadata
import re
import html
from email.header import decode_header, make_header


# 목록 조회를 위해 이메일 본문 미리보기를 하는 시리얼라이저.
class EmailPreviewSerializer(serializers.ModelSerializer):
    preview = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = EmailContent
        fields = [
            "subject",
            "from_header",
            "date",
            "preview",  # 본문 대신 미리보기 필드 preview 사용.
        ]

    def get_subject(self, obj) -> str:
        """RFC 2047 형식으로 인코딩된 이메일 제목을 디코딩하여 반환합니다."""
        if not obj.subject:
            return ""
        # decode_header는 (디코딩된 바이트, 인코딩)의 리스트를 반환
        decoded_parts = decode_header(obj.subject)
        # make_header를 사용하여 올바르게 문자열로 조합
        return str(make_header(decoded_parts))

    def get_preview(self, obj) -> str:
        """
        본문 내용의 미리보기를 생성합니다.
        text_body가 있으면 사용하고, 없으면 html_body에서 불필요한 부분을 제거하여 사용합니다.
        """
        source_text = ""
        if obj.text_body:
            source_text = obj.text_body
        elif obj.html_body:
            # 0. HTML 엔티티 디코딩 (e.g., &nbsp; -> ' ')
            text = html.unescape(obj.html_body)
            # 1. <style>과 <script> 블록 제거
            text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
            # 2. HTML 주석 제거
            text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
            # 3. 나머지 HTML 태그 제거
            text = re.sub(r"<[^>]+>", "", text)
            source_text = text

        if source_text:
            # 4. 여러 공백과 개행을 하나의 스페이스로 합치고 양 끝 공백 제거
            clean_text = re.sub(r"\s+", " ", source_text).strip()
            return clean_text[:150]

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
