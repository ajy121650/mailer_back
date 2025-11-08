from django.urls import path
from .views import EmailMetadataListView, EmailUpdateView, EmailSummarizeView

app_name = "email_metadata"

urlpatterns = [
    path("", EmailMetadataListView.as_view(), name="email-list"),
    path("<int:pk>/", EmailUpdateView.as_view(), name="email-detail"),
    path("<int:pk>/summarize/", EmailSummarizeView.as_view(resummarize=False), name="email-summarize"),
    path("<int:pk>/resummarize/", EmailSummarizeView.as_view(resummarize=True), name="email-resummarize"),
]
