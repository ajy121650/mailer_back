from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema  # Import extend_schema
from email_account.models import EmailAccount
from email_content.models import EmailContent
from email_metadata.models import EmailMetadata
from .serializers import EmailSendSerializer
from .service.smtp import send_mail_via_smtp, SMTPAuth

import smtplib


@extend_schema(
    summary="이메일 전송",
    description="로그인한 사용자의 이메일 계정을 통해 이메일을 발송합니다. 성공적으로 발송된 이메일은 발신자의 '보낸 편지함'에 저장됩니다.",
    request=EmailSendSerializer,
    responses={
        200: {
            "description": "이메일이 성공적으로 전송되었습니다.",
            "example": {"message": "이메일이 성공적으로 전송되었습니다."},
        },
        400: {"description": "잘못된 요청 데이터", "example": {"account_id": ["이 필드는 필수입니다."]}},
        401: {
            "description": "인증 실패 (예: SMTP 로그인 실패)",
            "example": {"error": "SMTP 인증에 실패했습니다. 계정 정보를 확인해주세요."},
        },
        403: {
            "description": "권한 없음 (예: 다른 사용자 계정으로 발송 시도)",
            "example": {"error": "해당 계정을 찾을 수 없거나, 접근 권한이 없습니다."},
        },  # 403, 404 예시 통합
        404: {
            "description": "계정을 찾을 수 없음",
            "example": {"error": "해당 계정을 찾을 수 없거나, 접근 권한이 없습니다."},
        },  # 403, 404 예시 통합
        500: {"description": "서버 내부 오류", "example": {"error": "이메일 전송 중 오류가 발생했습니다: 오류 메시지"}},
    },
    tags=["email"],  # API 그룹을 "email"로 지정
)
class SendEmailView(APIView):
    """
    이메일을 전송하는 API View
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EmailSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        account_id = validated_data["account_id"]

        # 1. 요청자가 소유한 EmailAccount인지 확인 (보안)
        try:
            account = get_object_or_404(EmailAccount, id=account_id, user=request.user)
        except EmailAccount.DoesNotExist:
            return Response(
                {"error": "해당 계정을 찾을 수 없거나, 접근 권한이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not account.is_valid:
            return Response(
                {"error": "계정이 유효하지 않습니다. 계정 정보를 다시 확인해주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. SMTP 인증 정보 준비 및 실제 메일 발송
        try:
            with transaction.atomic():
                # 2-1. SMTP 인증 객체 생성
                auth = SMTPAuth(
                    username=account.address,
                    password=account.email_password,
                    domain_hint=account.domain,
                )

                # 2-2. smtp.py의 함수를 호출하여 메일 발송
                send_result = send_mail_via_smtp(
                    auth=auth,
                    sender=account.address,
                    to=validated_data["to"],
                    cc=validated_data.get("cc"),
                    bcc=validated_data.get("bcc"),
                    subject=validated_data["subject"],
                    text_body=None if validated_data["is_html"] else validated_data["body"],
                    html_body=validated_data["body"] if validated_data["is_html"] else None,
                )

                # 메일 발송 실패 시 롤백
                if not send_result["accepted"]:
                    raise smtplib.SMTPException("모든 수신자에게 메일 발송을 실패했습니다.")

                # 3. DB에 EmailContent, EmailMetadata 저장
                # 3-1. EmailContent 생성
                email_content = EmailContent.objects.create(
                    message_id=send_result.get("message_id"),
                    subject=validated_data["subject"],
                    from_header=account.address,
                    to_header=validated_data["to"],
                    cc_header=validated_data.get("cc"),
                    bcc_header=validated_data.get("bcc"),
                    text_body=None if validated_data["is_html"] else validated_data["body"],
                    html_body=validated_data["body"] if validated_data["is_html"] else None,
                    date=timezone.now(),
                )

                # 3-2. EmailMetadata 생성 (보낸편지함)
                EmailMetadata.objects.create(
                    account=account,
                    email=email_content,
                    folder="sent",
                    is_read=True,
                    received_at=timezone.now(),
                )

        except smtplib.SMTPAuthenticationError:
            account.is_valid = False
            account.save()
            return Response(
                {"error": "SMTP 인증에 실패했습니다. 계정 정보를 확인해주세요."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            # 기타 예외 처리
            return Response(
                {"error": f"이메일 전송 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"message": "이메일이 성공적으로 전송되었습니다."}, status=status.HTTP_200_OK)
