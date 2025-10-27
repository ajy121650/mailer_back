from .views import TemplateListView, TemplateDetailView
from django.urls import path

app_name = "templates"

urlpatterns = [
    path("", TemplateListView.as_view(), name="template-list"),
    path("<int:pk>/", TemplateDetailView.as_view(), name="template-detail"),
]
