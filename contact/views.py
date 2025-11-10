from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiTypes,
)

from .models import Contact
from .serializers import ContactSerializer
from email_account.models import EmailAccount


@extend_schema_view(
    get=extend_schema(
        summary="즐겨찾기 주소록 목록 조회",
        description="특정 이메일 계정(`account_id`)에 등록된 즐겨찾기 주소 목록을 조회합니다.",
        responses=ContactSerializer(many=True),
        examples=[
            OpenApiExample(
                "조회 성공",
                value=[{"id": 1, "address": "friend@example.com"}],
                response_only=True,
            )
        ],
    ),
    post=extend_schema(
        summary="즐겨찾기 주소 추가",
        description="특정 이메일 계정(`account_id`)에 새로운 주소를 즐겨찾기로 추가합니다.",
        request=ContactSerializer,
        responses={201: ContactSerializer, 400: OpenApiTypes.OBJECT, 409: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "추가 성공",
                value={"id": 3, "address": "new_friend@example.com"},
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "중복 추가 시도",
                value={"detail": "This address is already in the contact list."},
                response_only=True,
                status_codes=["409"],
            ),
        ],
    ),
)
class ContactListCreateView(generics.ListCreateAPIView):
    """
    GET: 특정 계정의 주소록 목록 조회
    POST: 특정 계정에 새 주소 추가
    """

    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        """요청된 account_id에 대한 소유권을 먼저 확인합니다."""
        self.account = get_object_or_404(EmailAccount, pk=kwargs["account_id"], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """소유권이 확인된 계정의 주소록만 반환합니다."""
        return Contact.objects.filter(account=self.account)

    def create(self, request, *args, **kwargs):
        address = request.data.get("address")

        # 1. 주소 중복 검사
        if self.get_queryset().filter(address=address).exists():
            return Response(
                {"detail": "This address is already in the contact list."},
                status=status.HTTP_409_CONFLICT,
            )

        # 2. 기본 유효성 검사 및 객체 생성
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(account=self.account)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema_view(
    patch=extend_schema(
        summary="즐겨찾기 주소 수정",
        description="특정 연락처(`contact_id`)의 주소를 수정합니다.",
        request=ContactSerializer,
        responses={200: ContactSerializer, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "수정 성공",
                value={"id": 3, "address": "re_friend@example.com"},
                response_only=True,
            )
        ],
    ),
    delete=extend_schema(
        summary="즐겨찾기 주소 삭제",
        description="특정 연락처(`contact_id`)를 즐겨찾기에서 삭제합니다.",
        responses={204: None, 404: OpenApiTypes.OBJECT},
    ),
)
class ContactDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    """
    특정 주소록 항목을 수정하거나 삭제합니다.
    PATCH: /api/contact/{contact_id}/
    DELETE: /api/contact/{contact_id}/
    """

    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"
    lookup_url_kwarg = "contact_id"
    http_method_names = ["patch", "delete", "head", "options"]

    def get_queryset(self):
        """현재 로그인된 사용자가 소유한 모든 이메일 계정에 속한 주소록만 조회합니다."""
        return Contact.objects.filter(account__user=self.request.user)
