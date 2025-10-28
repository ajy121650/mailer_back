# Create your views here.
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiTypes
from drf_spectacular.utils import OpenApiExample
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
import requests


############################################ 테스트용 #################################
# sign in 된 유저 정보 조회 (인증 필요) test용 지워도 됨
@extend_schema(
    summary="내 정보 조회",
    description="로그인된 사용자의 정보를 반환합니다.",
    responses={
        200: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "정상 응답",
            value={"user_id": "user_xxxxxxxxxxxx"},
            response_only=True,
        )
    ],
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # request.user: 우리 DB의 User
        # request.auth: Clerk JWT payload (sub, sid, ...)
        return Response(
            {
                "user_id": request.user.user_id,
            }
        )


# 헬스체크 (공개)
@extend_schema(
    summary="서버 헬스 체크",
    description="서버의 정상 동작 여부를 확인합니다.",
    responses={200: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            "정상 응답",
            value={"ok": True},
            response_only=True,
        )
    ],
)
class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"ok": True})


#   (선택) 서버 강제 로그아웃: Clerk 세션 revoke
#    일반 로그아웃은 프론트에서 처리하면 되고,
#    보안상 필요할 때만 사용 (예: 관리자 강제 로그아웃)
@extend_schema(
    summary="강제 로그아웃",
    description="보안상 필요시 서버에서 강제로 사용자의 세션을 만료시킵니다.",
    request=None,  # 요청 본문이 없음을 명시
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample("정상 응답", value={"ok": True}, response_only=True),
        OpenApiExample(
            "세션 ID 없음",
            value={"error": "No session id in token"},
            status_codes=["400"],
            response_only=True,
        ),
    ],
)
class SignOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Clerk 토큰 payload에서 세션 ID(sid) 추출
        payload = request.auth or {}
        sid = payload.get("sid")
        if not sid:
            return Response({"error": "No session id in token"}, status=400)

        # Clerk 서버 API로 해당 세션 revoke
        r = requests.post(
            f"{settings.CLERK_API_BASE}/sessions/{sid}/revoke",
            headers={"Authorization": f"Bearer {settings.CLERK_API_KEY}"},
            timeout=5,
        )
        if r.status_code >= 400:
            try:
                return Response(r.json(), status=r.status_code)
            except Exception:
                return Response({"error": "Failed to revoke session"}, status=r.status_code)

        return Response({"ok": True})


#######################################################################################
