from django.db import models
from email_content.models import EmailContent as Emails


# Create your models here.
class Attachment(models.Model):
    email = models.ForeignKey(Emails, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=50)
    file_size = models.FloatField()
    file_path = models.CharField(max_length=255)  # S3 key 등
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name
