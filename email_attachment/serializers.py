from rest_framework import serializers
from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """첨부파일 정보를 위한 시리얼라이저"""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "file_name",
            "mime_type",
            "file_size",
            "download_url",
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        """첨부파일을 다운로드할 수 있는 URL을 생성합니다."""
        request = self.context.get("request")
        if request:
            # build_absolute_uri를 사용하면 request의 호스트 정보를 바탕으로 전체 URL을 만들어줍니다.
            # 예: http://localhost:8000/api/attachments/1/download
            return request.build_absolute_uri(f"/api/attachments/{obj.id}/download/")

        # request 컨텍스트가 없는 경우 (예: 쉘에서 직접 시리얼라이저 사용)
        # settings.MEDIA_URL을 기반으로 경로를 구성할 수 있으나, 이 경우엔 다운로드 view를 통하도록 일관성 유지
        return f"/api/attachments/{obj.id}/download/"
