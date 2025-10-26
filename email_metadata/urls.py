from django.urls import path
from .views import EmailMetadataListView, EmailUpdateView

app_name = "email_metadata"

urlpatterns = [
    path("", EmailMetadataListView.as_view(), name="email-list"),
    path("<int:pk>/", EmailUpdateView.as_view(), name="email-detail"),
]
