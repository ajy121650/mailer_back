from rest_framework import generics, permissions, serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q
from .models import EmailMetadata
from .serializers import (
    EmailDetailSerializer,
    EmailUpdateSerializer,
    EmailMetadataListSerializer,
)
from email_account.models import EmailAccount

User = get_user_model()


class TestPermission(permissions.BasePermission):
    """
    (임시 테스트용 - 보안에 취약함)
    로그인된 사용자이거나, 테스트를 위한 'user_id' 쿼리 파라미터가 있을 경우에만 접근을 허용합니다.
    user_id가 있으면 해당 사용자를 찾아서 request.user에 주입합니다.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True

        user_id = request.query_params.get("user_id")
        if user_id:
            try:
                request.user = User.objects.get(pk=user_id)
                return True
            except User.DoesNotExist:
                return False

        return False


@extend_schema(
    description="""
        메일 통합 조회를 위핸 API View입니다. 해당 API로 가능한 것:
        1. 이메일 계정 별 이메일 조회. (생략 시 전체 조회)
        2. 폴더 별 이메일 조회. 받은(inbox), 보낸(sent), 별표(starred), 스팸(spam), 휴지통(trash). (생략 시 전체 폴더)
        3. 검색어로 이메일 필터링. (제목, 보낸사람, 내용, 수신자 대상)""",
    parameters=[
        OpenApiParameter(
            name="user_id",
            description="(임시 테스트용) 로그인 기능 구현 전, 테스트할 사용자의 ID를 직접 입력합니다.",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="folder",
            description="폴더 이름으로 필터링합니다.",
            required=False,
            type=OpenApiTypes.STR,
            enum=[choice[0] for choice in EmailMetadata.FOLDER_CHOICES],
        ),
        OpenApiParameter(
            name="accounts",
            description="콤마(,)로 구분된 이메일 주소 목록으로 필터링합니다. 생략 시 모든 계정을 포함합니다.",
            required=False,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name="query",
            description="검색어로 필터링합니다. 보낸사람, 제목, 내용, 수신자 필드를 대상으로 검색합니다.",
            required=False,
            type=OpenApiTypes.STR,
        ),
    ]
)
class EmailMetadataListView(generics.ListAPIView):
    """메일 통합 조회를 위한 API View"""

    serializer_class = EmailMetadataListSerializer
    permission_classes = [TestPermission]

    def get_queryset(self):
        """
        요청에 따라 쿼리셋을 필터링하고 정렬하여 반환합니다.
        'sent' 폴더와 그 외 폴더의 로직을 분리하여 처리합니다.
        """
        user = self.request.user

        if not user.is_authenticated:
            return EmailMetadata.objects.none()

        folder = self.request.query_params.get("folder", None)
        accounts_param = self.request.query_params.get("accounts", None)
        search_query = self.request.query_params.get("query", None)

        if folder == "sent":
            user_email_addresses = list(
                EmailAccount.objects.filter(user=user).values_list("address", flat=True)
            )
            # from_header는 단일 주소 또는 다중 주소를 포함할 수 있으므로, __icontains 사용
            from_filters = [
                Q(email__from_header__icontains=addr) for addr in user_email_addresses
            ]
            # OR 조건으로 쿼리
            from_query = Q()
            for f in from_filters:
                from_query |= f

            queryset = EmailMetadata.objects.filter(from_query, account__user=user)
            order_by_field = "-email__date"
            account_filter_field = "account__address__in"

        else:
            queryset = EmailMetadata.objects.filter(account__user=user)
            order_by_field = "-received_at"
            account_filter_field = "account__address__in"

        if folder and folder != "sent":
            queryset = queryset.filter(folder=folder)

        # 투입한 accounts 파라미터가 있으면 해당 이메일 주소들로 필터링.
        if accounts_param:
            requested_emails = set(accounts_param.split(","))
            user_emails = set(
                EmailAccount.objects.filter(user=user).values_list("address", flat=True)
            )

            if not requested_emails.issubset(user_emails):
                invalid_accounts = sorted(list(requested_emails - user_emails))
                raise serializers.ValidationError(
                    f"You do not have permission for the following accounts: {invalid_accounts}"
                )

            queryset = queryset.filter(**{account_filter_field: list(requested_emails)})

        # 검색 쿼리가 있으면, 여러 필드에 걸쳐 검색
        if search_query:
            queryset = queryset.filter(
                Q(email__subject__icontains=search_query)
                | Q(email__from_header__icontains=search_query)
                | Q(email__text_body__icontains=search_query)
                | Q(email__to_header__icontains=search_query)  # JSONField 검색
            )

        return queryset.order_by(order_by_field)

@extend_schema(
    summary="개별 이메일의 조회, 설정, 삭제",
    description="""개별 이메일에 대한 거의 모든 작업을 할 수 있습니다.
특정 ID를 가진 이메일 하나에 대한 작업을 수행합니다.
1. GET: 이메일의 상세 정보를 조회합니다. (조회 시 자동으로 '읽음' 상태로 변경됨.)
2. PATCH: 이메일의 상태(폴더 바꾸기(휴지통, 중요메일함 등), 읽음 여부 설정 등)를 부분적으로 수정합니다.
3. DELETE:
    - 휴지통에 있지 않은 경우: 휴지통으로 이동시키고, 수정된 이메일 정보를 반환합니다. (상태 코드 200)
    - 휴지통에 있는 경우: 영구 삭제하고, 내용 없는 응답을 반환합니다. (상태 코드 204)
    """,
    request=EmailUpdateSerializer,
    responses={
        200: EmailDetailSerializer,
        204: None,  # 내용이 없는 성공 응답
    },
)
class EmailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """특정 이메일의 조회, 수정, 삭제를 위한 API View"""

    permission_classes = [TestPermission]
    queryset = EmailMetadata.objects.all()

    def get_serializer_class(self):
        """요청 메서드에 따라 다른 시리얼라이저를 반환합니다."""
        if self.request.method == "PATCH":
            return EmailUpdateSerializer
        return EmailDetailSerializer

    def get_queryset(self):
        """요청한 사용자가 소유한 이메일만 조회하도록 쿼리셋을 필터링합니다."""
        return super().get_queryset().filter(account__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """
        상세 조회 시, 해당 이메일을 '읽음' 상태로 자동 변경합니다.
        """
        instance = self.get_object()
        if not instance.is_read:
            instance.is_read = True
            instance.save(update_fields=["is_read"])
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        '삭제' 요청을 컨텍스트에 맞게 처리합니다.
        - 휴지통에 있지 않은 경우: 휴지통으로 이동시킵니다.
        - 휴지통에 있는 경우: 영구 삭제합니다.
        """
        instance = self.get_object()
        if instance.folder != "trash":
            # 휴지통으로 이동
            instance.folder = "trash"
            instance.save(update_fields=["folder"])
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        else:
            # 영구 삭제 (기본 destroy 호출)
            return super().destroy(request, *args, **kwargs)