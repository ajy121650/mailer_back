from rest_framework import generics, permissions, serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Mailbox
from .serializers import MailboxSerializer
from user.models import EmailAccount

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
    parameters=[
        OpenApiParameter(
            name="user_id",
            description="(임시 테스트용) 로그인 기능 구현 전, 테스트할 사용자의 ID를 직접 입력합니다.",
            required=False,  # 실제 인증 구현 후에는 True 또는 삭제
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="folder",
            description="폴더 이름으로 필터링합니다.",
            required=False,
            type=OpenApiTypes.STR,
            enum=Mailbox.FolderType.values,
        ),
        OpenApiParameter(
            name="accounts",
            description="콤마(,)로 구분된 이메일 주소 목록으로 필터링합니다. 생략 시 모든 계정을 포함합니다.",
            required=False,
            type=OpenApiTypes.STR,
        ),
    ]
)
class MailboxListView(generics.ListAPIView):
    """메일 통합 조회를 위한 API View"""

    serializer_class = MailboxSerializer
    permission_classes = [TestPermission]

    def get_queryset(self):
        """
        요청에 따라 쿼리셋을 필터링하고 정렬하여 반환합니다.
        'sent' 폴더와 그 외 폴더의 로직을 분리하여 처리합니다.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Mailbox.objects.none()

        folder = self.request.query_params.get("folder", None)
        accounts_param = self.request.query_params.get("accounts", None)

        if folder == "sent":
            user_email_addresses = list(EmailAccount.objects.filter(user=user).values_list("email_address", flat=True))
            queryset = Mailbox.objects.filter(email__from_address__in=user_email_addresses)
            order_by_field = "-email__sent_at"
            account_filter_field = "email__from_address__in"
        else:
            queryset = Mailbox.objects.filter(account__user=user)
            order_by_field = "-received_at"
            account_filter_field = "account__email_address__in"

        if folder and folder != "sent":
            queryset = queryset.filter(folder=folder)

        # 투입한 accounts 파라미터가 있으면 해당 이메일 주소들로 필터링.
        if accounts_param:
            requested_emails = set(accounts_param.split(","))
            user_emails = set(EmailAccount.objects.filter(user=user).values_list("email_address", flat=True))

            if not requested_emails.issubset(user_emails):
                invalid_accounts = sorted(list(requested_emails - user_emails))
                raise serializers.ValidationError(
                    f"You do not have permission for the following accounts: {invalid_accounts}"
                )

            queryset = queryset.filter(**{account_filter_field: list(requested_emails)})

        return queryset.order_by(order_by_field)
