from django.urls import path

### views import example
from .views import MeView, HealthView, SignOutView

###

app_name = "users"

urlpatterns = [
    path("me/", MeView.as_view()),  # test용, 지워도 됨
    path("health/", HealthView.as_view()),  # 헬스체크
    path("signout/", SignOutView.as_view()),  # (선택) 서버 강제 로그아웃
]
