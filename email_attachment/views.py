from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from urllib.parse import quote

from .models import Attachment
from email_metadata.models import EmailMetadata


class AttachmentDownloadView(APIView):
    """
    첨부파일을 안전하게 다운로드하기 위한 View
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        """
        요청한 사용자가 소유한 이메일에 속한 첨부파일인지 확인하고, 파일을 제공합니다.
        """
        user = request.user

        # 1. 첨부파일 객체 조회 및 권한 검사
        try:
            # 복잡한 조인 쿼리를 통해 현재 로그인한 사용자가 접근 권한이 있는 첨부파일인지 한 번에 확인
            attachment = get_object_or_404(
                Attachment,
                pk=pk,
                email__in=EmailMetadata.objects.filter(account__user=user).values_list("email", flat=True),
            )
        except Http404:
            return HttpResponse("파일을 찾을 수 없거나 접근 권한이 없습니다.", status=404)

        # 2. 파일 시스템에서 파일 경로 확인
        # Attachment 모델의 file_path는 'EmailAttachments/...' 형태의 상대 경로를 가짐
        file_path = os.path.join(settings.BASE_DIR, attachment.file_path)

        if not os.path.exists(file_path):
            # DB에는 기록이 있으나 실제 파일이 없는 경우
            return HttpResponse("서버에서 파일을 찾을 수 없습니다.", status=404)

        # 3. 파일을 열고 HttpResponse로 반환
        try:
            with open(file_path, "rb") as f:
                response = HttpResponse(f.read(), content_type=attachment.mime_type)

                # 파일 이름을 UTF-8로 인코딩하고, URL 인코딩을 적용하여 헤더에 추가
                encoded_filename = quote(attachment.file_name)
                response["Content-Disposition"] = f"attachment; filename*=UTF-8'' {encoded_filename}"

                return response
        except IOError:
            return HttpResponse("파일을 읽는 중 오류가 발생했습니다.", status=500)
