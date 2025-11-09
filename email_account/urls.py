from django.urls import path
from .views import (
    EmailSyncView,
    EmailAccountListCreateView,
    EmailAccountDestroyView,
    EmailAccountProfileUpdateView,
)

app_name = "email_accounts"

urlpatterns = [
    path("<int:pk>/sync/", EmailSyncView.as_view(), name="메일 최신 동기화"),
    # 이메일 계정 CRUD
    path("", EmailAccountListCreateView.as_view(), name="메일계정 연동 및 조회"),
    path("<int:account_id>/", EmailAccountDestroyView.as_view(), name="메일계정 삭제"),
    path(
        "<int:account_id>/profile/",
        EmailAccountProfileUpdateView.as_view(),
        name="메일계정 프로필 수정",
    ),
]
