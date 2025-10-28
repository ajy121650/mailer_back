from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiExample
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import EmailAccount
from email_content.proto import fetch_and_store_emails


@extend_schema(
    summary="이메일 수동 동기화",
    description="특정 이메일 계정의 메일을 수동으로 동기화합니다.",
    request=None,  # 요청 본문이 없음을 명시
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "동기화 성공",
            value={"message": "user@example.com의 동기화가 완료되었습니다."},
            response_only=True,
        ),
        OpenApiExample(
            "계정 없음",
            value={"error": "계정을 찾을 수 없거나 권한이 없습니다."},
            status_codes=["404"],
            response_only=True,
        ),
        OpenApiExample(
            "IMAP 동기화 실패",
            value={"error": "IMAP 동기화 실패: [Errno 111] Connection refused"},
            status_codes=["500"],
            response_only=True,
        ),
    ],
)
class EmailSyncView(APIView):
    """특정 이메일 계정의 메일을 수동으로 동기화합니다."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """
        계정 소유권과 유효성을 확인한 후,
        fetch_and_store_emails 함수를 호출하여 동기화를 수행합니다.
        """
        try:
            # 1. 계정 조회 (소유권 확인 포함)
            account = EmailAccount.objects.get(pk=pk, user=request.user)
        except EmailAccount.DoesNotExist:
            return Response(
                {"error": "계정을 찾을 수 없거나 권한이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. 계정 유효성 확인
        if not account.is_valid:
            return Response(
                {"error": "인증되지 않았거나 비활성화된 계정."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 3. 동기화 함수 호출
            fetch_and_store_emails(address=account.address)
        except ValueError as e:
            # IMAP 연결 실패 등 동기화 중 발생한 오류 처리
            return Response(
                {"error": f"IMAP 동기화 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            # 기타 예외 처리
            return Response(
                {"error": f"알 수 없는 오류 발생: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. 성공 응답 반환
        return Response(
            {"message": f"{account.address}의 동기화가 완료되었습니다."},
            status=status.HTTP_200_OK,
        )
