from django.urls import path
from .views import MailboxListView

urlpatterns = [
    path('', MailboxListView.as_view(), name='mailbox-list'),
]
