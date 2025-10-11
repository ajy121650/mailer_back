from django.db import models
from user.models import User


# Create your models here.
class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="templates")
    template_content = models.CharField(max_length=255)  # ERD를 그대로 따르면 CharField

    def __str__(self):
        return f"Template#{self.id} of {self.user_id}"
