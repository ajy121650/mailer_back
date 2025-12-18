from .views import (
    ViewTemplateListView,
    ViewTemplateDetailView,
    MyTemplateListView,
    MyTemplateDetailView,
    MyTemplateCreateView,
)
from django.urls import path

app_name = "templates"

urlpatterns = [
    path("viewtemplate/", ViewTemplateListView.as_view(), name="template-list"),
    path("viewtemplate/<int:pk>/", ViewTemplateDetailView.as_view(), name="template-detail"),
    path("mytemplate/create/", MyTemplateCreateView.as_view(), name="my-template-create"),
    path("mytemplate/list/<int:pk>/", MyTemplateListView.as_view(), name="my-template-list"),
    path("mytemplate/<int:pk>/", MyTemplateDetailView.as_view(), name="my-template-detail"),
]
