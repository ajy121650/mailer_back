import requests
from functools import lru_cache
from jose import jwt
from django.conf import settings
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
