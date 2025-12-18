from django.urls import path
from .views import AttachmentDownloadView

app_name = "email_attachment"

urlpatterns = [
    path("<int:pk>/download/", AttachmentDownloadView.as_view(), name="attachment-download"),
]
