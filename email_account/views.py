from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiTypes,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from .models import EmailAccount
from email_content.service.imap import fetch_and_store_emails
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

####### 이메일 계정 연동 관련 임포트 #########
from .serializers import (
    EmailAccountSerializer,
    EmailAccountCreateSerializer,
    EmailAccountProfileSerializer,
)

logger = logging.getLogger(__name__)

####### 스레드 풀 설정 #########
# EC2 프리티어 (CPU 1개)에서도 여러 사용자를 동시 처리하기 위함
# I/O 바운드 작업(IMAP, DB)이므로 CPU 코어 수보다 많이 설정 가능
CPU_COUNT = os.cpu_count() or 1
THREAD_POOL_SIZE = max(10, CPU_COUNT * 4)  # CPU 1개면 10개 스레드, CPU 4개면 16개 스레드
EXECUTOR = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)

logger.info(f"[Thread Pool] CPU: {CPU_COUNT}개, 스레드풀 크기: {THREAD_POOL_SIZE}")

####### 이메일 계정 연동 관련 임포트 #########


async def _sync_emails_async(address: str, account_id: int, timeout: int = 300):
    """
    asyncio를 사용한 비동기 이메일 동기화.
    논블로킹 I/O로 실행되므로 다른 요청이 동시에 처리될 수 있습니다.

    Args:
        address: 이메일 주소
        account_id: 계정 ID
        timeout: 최대 대기 시간 (초, 기본값 300초 = 5분)
    """
    try:
        # Django ORM은 동기식이므로 run_in_executor를 통해 별도 스레드에서 실행
        # 커스텀 EXECUTOR를 사용하여 동시에 처리할 수 있는 스레드 수를 증가
        loop = asyncio.get_event_loop()
        synced_count = await asyncio.wait_for(
            loop.run_in_executor(
                EXECUTOR,  # ← 커스텀 스레드풀 사용
                fetch_and_store_emails,
                address,
            ),
            timeout=timeout,
        )
        logger.info(f"[Async Sync] account_id={account_id}, address={address}, synced={synced_count}")
        return synced_count
    except asyncio.TimeoutError:
        error_msg = f"이메일 동기화 시간 초과 (제한시간: {timeout}초)"
        logger.error(f"[Async Sync Timeout] account_id={account_id}, address={address}, timeout={timeout}s")
        raise TimeoutError(error_msg)
    except Exception as e:
        logger.error(f"[Async Sync Error] account_id={account_id}, address={address}, error={str(e)}")
        raise


@extend_schema(
    summary="이메일 수동 동기화 (async)",
    description="특정 이메일 계정의 메일을 비동기로 동기화합니다. 동기화가 완료될 때까지 요청을 대기하지만, 그 사이에 다른 요청은 처리 가능합니다.",
    request=None,
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "동기화 성공",
            value={"message": "user@example.com의 동기화가 완료되었습니다.", "synced_count": 15},
            response_only=True,
        ),
        OpenApiExample(
            "계정 없음",
            value={"error": "계정을 찾을 수 없거나 권한이 없습니다."},
            status_codes=["404"],
            response_only=True,
        ),
    ],
)
class EmailSyncView(APIView):
    """특정 이메일 계정의 메일을 비동기로 동기화합니다."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """
        계정 소유권과 유효성을 확인한 후,
        비동기로 이메일 동기화를 수행하고,
        완료 후 응답을 반환합니다.

        동기화 중에도 다른 요청은 처리됩니다.
        (내부적으로 asyncio 이벤트 루프에서 실행)
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
            # 3. 비동기 동기화를 스레드에서 실행
            # 이 스레드는 비동기 이벤트 루프를 가지고 있어서
            # 다른 요청들이 동시에 처리될 수 있음
            synced_count = self._run_async_sync(account.address, account.id)

            # 4. 성공 응답 반환
            return Response(
                {
                    "message": f"{account.address}의 동기화가 완료되었습니다.",
                    "synced_count": synced_count,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Sync error for {account.address}: {str(e)}")
            return Response(
                {"error": f"동기화 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _run_async_sync(address: str, account_id: int, timeout: int = 300):
        """
        asyncio 이벤트 루프를 생성하고 비동기 동기화를 실행합니다.

        각 요청마다 독립적인 이벤트 루프를 가지므로
        여러 요청이 동시에 처리될 수 있습니다.
        """
        try:
            # 새로운 이벤트 루프 생성 (스레드별 독립적)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 비동기 함수 실행
                synced_count = loop.run_until_complete(_sync_emails_async(address, account_id, timeout))
                return synced_count
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"[Async Sync Error] account_id={account_id}, address={address}, error={str(e)}")
            raise


# @extend_schema(
#     summary="이메일 수동 동기화",
#     description="특정 이메일 계정의 메일을 수동으로 동기화합니다. 새로 동기화된 메일의 개수를 반환합니다.",
#     request=None,  # 요청 본문이 없음을 명시
#     responses={
#         200: OpenApiTypes.OBJECT,
#         400: OpenApiTypes.OBJECT,
#         404: OpenApiTypes.OBJECT,
#         500: OpenApiTypes.OBJECT,
#     },
#     examples=[
#         OpenApiExample(
#             "동기화 성공 (새 메일 15개)",
#             value={"message": "user@example.com의 동기화가 완료되었습니다.", "synced_count": 15},
#             response_only=True,
#         ),
#         OpenApiExample(
#             "동기화 성공 (새 메일 없음)",
#             value={"message": "user@example.com의 동기화가 완료되었습니다.", "synced_count": 0},
#             response_only=True,
#         ),
#         OpenApiExample(
#             "계정 없음",
#             value={"error": "계정을 찾을 수 없거나 권한이 없습니다."},
#             status_codes=["404"],
#             response_only=True,
#         ),
#         OpenApiExample(
#             "IMAP 동기화 실패",
#             value={"error": "IMAP 동기화 실패: IMAP 연결 또는 로그인 실패: [Errno 111] Connection refused"},
#             status_codes=["500"],
#             response_only=True,
#         ),
#     ],
# )
# class EmailSyncView(APIView):
#     """특정 이메일 계정의 메일을 수동으로 동기화합니다."""

#     permission_classes = [IsAuthenticated]

#     def post(self, request, pk):
#         """
#         계정 소유권과 유효성을 확인한 후,
#         fetch_and_store_emails 함수를 호출하여 동기화를 수행하고,
#         동기화된 메일의 개수를 반환합니다.
#         """
#         try:
#             # 1. 계정 조회 (소유권 확인 포함)
#             account = EmailAccount.objects.get(pk=pk, user=request.user)
#         except EmailAccount.DoesNotExist:
#             return Response(
#                 {"error": "계정을 찾을 수 없거나 권한이 없습니다."},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         # 2. 계정 유효성 확인
#         if not account.is_valid:
#             return Response(
#                 {"error": "인증되지 않았거나 비활성화된 계정."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             # 3. 동기화 함수 호출 및 결과 저장
#             synced_count = fetch_and_store_emails(address=account.address)
#         except ValueError as e:
#             # IMAP 연결 실패 등 동기화 중 발생한 예측된 오류 처리
#             return Response(
#                 {"error": f"IMAP 동기화 실패: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         except Exception as e:
#             # 로깅된 기타 예외 처리
#             return Response(
#                 {"error": f"알 수 없는 오류 발생: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         # 4. 성공 응답 반환
#         return Response(
#             {
#                 "message": f"{account.address}의 동기화가 완료되었습니다.",
#                 "synced_count": synced_count,
#             },
#             status=status.HTTP_200_OK,
#         )


# ===================================================================
# 이메일 계정 관리 (CRUD)
# ===================================================================


@extend_schema_view(
    get=extend_schema(
        summary="연동된 메일 계정 목록 조회",
        description="현재 로그인된 사용자가 연동한 모든 이메일 계정 목록을 조회합니다.",
        responses=EmailAccountSerializer(many=True),
        examples=[
            OpenApiExample(
                "조회 성공",
                value=[
                    {
                        "id": 1,
                        "address": "user1@example.com",
                        "domain": "example.com",
                        "is_valid": True,
                        "last_synced": "2025-10-28T10:00:00Z",
                    }
                ],
                response_only=True,
            )
        ],
    ),
    post=extend_schema(
        summary="메일 계정 연동",
        description="새로운 이메일 계정을 연동합니다. 비밀번호는 암호화되어 저장됩니다.",
        request=EmailAccountCreateSerializer,
        responses={
            201: EmailAccountSerializer,
            400: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "생성 성공",
                value={
                    "id": 2,
                    "address": "new_user@gmail.com",
                    "domain": "gmail",
                    "is_valid": True,
                    "last_synced": None,
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "유효성 검사 실패",
                value={"address": ["Enter a valid email address."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "이미 등록된 계정",
                value={"detail": "This email account is already registered."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    ),
)
class EmailAccountListCreateView(generics.ListCreateAPIView):
    """
    GET: 로그인된 사용자의 이메일 계정 목록을 조회합니다.
    POST: 새 이메일 계정을 연동합니다.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 로그인된 사용자의 계정만 조회합니다."""
        return EmailAccount.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """요청 메서드에 따라 다른 Serializer를 반환합니다."""
        if self.request.method == "POST":
            return EmailAccountCreateSerializer
        return EmailAccountSerializer

    def perform_create(self, serializer):
        """새 계정을 생성할 때 현재 로그인된 사용자를 소유자로 설정합니다."""
        serializer.save(user=self.request.user)


@extend_schema(
    summary="연동된 메일 계정 삭제",
    description="지정된 ID의 이메일 계정 연동을 삭제합니다.",
    responses={204: None, 404: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample("삭제 성공", value=None, response_only=True, status_codes=["204"]),
        OpenApiExample(
            "찾을 수 없음 / 권한 없음",
            value={"detail": "Not found."},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
class EmailAccountDestroyView(generics.DestroyAPIView):
    """
    지정된 ID의 이메일 계정 연동을 삭제합니다.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "account_id"

    def get_queryset(self):
        """현재 로그인된 사용자의 계정 내에서만 삭제를 허용합니다."""
        return EmailAccount.objects.filter(user=self.request.user)


@extend_schema_view(
    patch=extend_schema(
        summary="메일 계정 프로필 설정/수정",
        description="지정된 이메일 계정의 프로필을 설정하거나 수정합니다. `PATCH` 메서드이므로, **변경하려는 필드만** 요청 바디에 담아 보낼 수 있습니다. 해당 프로필은 이후 스팸 필터링에 사용됩니다.",
        request=EmailAccountProfileSerializer,
        responses={200: EmailAccountProfileSerializer, 400: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "수정 성공",
                value={
                    "job": "데이터 분석가",
                    "usage": "학교용",
                    "interests": ["금융", "부동산"],
                },
                response_only=True,
            ),
            OpenApiExample(
                "유효성 검사 실패",
                value={"interests": ["This field must be a list."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
)
class EmailAccountProfileUpdateView(generics.UpdateAPIView):
    """
    지정된 이메일 계정의 프로필(job, usage, interests)을 설정하거나 수정합니다.
    """

    http_method_names = ["patch", "head", "options"]
    permission_classes = [IsAuthenticated]
    serializer_class = EmailAccountProfileSerializer
    lookup_field = "id"
    lookup_url_kwarg = "account_id"

    def get_queryset(self):
        """현재 로그인된 사용자의 계정 내에서만 수정을 허용합니다."""
        return EmailAccount.objects.filter(user=self.request.user)
