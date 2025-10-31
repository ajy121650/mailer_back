import requests
from functools import lru_cache
from jose import jwt
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions
from .models import User


@lru_cache(maxsize=1)
def _fetch_jwks():
    resp = requests.get(settings.CLERK_JWKS_URL, timeout=5)
    resp.raise_for_status()
    return resp.json()


def _get_public_key(token):
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    for key in _fetch_jwks().get("keys", []):
        if key.get("kid") == kid:
            # jose가 JWK를 키 객체로 바꿔서 쓸 수 있게 해줌
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    raise exceptions.AuthenticationFailed("Public key not found for token")


class ClerkAuthentication(authentication.BaseAuthentication):
    """
    Authorization: Bearer <clerk session token or JWT template token>
    - iss 검증: settings.CLERK_ISSUER
    - aud 검증: (JWT Template 사용 시) settings.CLERK_AUDIENCE
    """

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None  # 다른 인증과 혼합 사용 가능

        token = auth.split(" ", 1)[1].strip()
        try:
            public_key = _get_public_key(token)
            opts = {"verify_aud": settings.CLERK_AUDIENCE is not None}
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                audience=settings.CLERK_AUDIENCE,
                options=opts,
            )
            # exp/nbf/iat 자동 검증 (python-jose 기본)
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise exceptions.AuthenticationFailed("No sub in token")

        # 우리 DB에 유저 동기화 (없으면 생성)
        user, _created = User.objects.get_or_create(user_id=clerk_user_id)
        # DRF는 (user, auth) 튜플을 반환해야 함. auth에 payload를 넘기면 뷰에서 참조 가능
        return (user, payload)


######################## API 테스트를 위한 임시 Authentication #############
class TestAuthentication(authentication.BaseAuthentication):
    """(API_TEST_MODE=True 일 때 사용) 모든 요청을 'testuser'로 자동 인증하는 테스트용 클래스"""

    def authenticate(self, request):
        # 무조건 'testuser'로 사용자를 찾거나, 없으면 생성
        user, _created = User.objects.get_or_create(user_id="testuser")

        # (인증된 사용자, 토큰 페이로드) 튜플을 반환
        # 토큰 페이로드는 테스트용 더미값을 넣어줌
        return (user, {"sub": user.user_id, "sid": "test_session"})


class TestAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "user.auth.TestAuthentication"
    name = "test_auth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "query",
            "name": "user_id",
            "description": "테스트용 인증을 위해 쿼리 파라미터에 user_id를 전달합니다.",
        }


######################## API 테스트를 위한 임시 Authentication ############
