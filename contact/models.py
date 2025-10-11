from django.db import models
from email_account.models import EmailAccount


# Create your models here.
class Contact(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name="contacts")
    address = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["account", "address"], name="uniq_contact_per_account"),
        ]
