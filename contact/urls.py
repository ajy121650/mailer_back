from django.urls import path
from .views import ContactListCreateView, ContactDetailView

app_name = "contacts"

urlpatterns = [
    path("<int:account_id>/", ContactListCreateView.as_view(), name="contact-list-create"),
    path("<int:contact_id>/", ContactDetailView.as_view(), name="contact-detail"),
]
