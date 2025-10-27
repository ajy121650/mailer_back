from django.urls import path
from .views import EmailSyncView

app_name = "email_accounts"

urlpatterns = [
    path("<int:pk>/sync/", EmailSyncView.as_view(), name="메일 최신 동기화"),
]
