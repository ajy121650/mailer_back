from django.db import models
from user.models import User


# Create your models here.
class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="templates")
    main_category = models.CharField(max_length=100, null=True, blank=True)
    sub_category = models.CharField(max_length=100, null=True, blank=True)
    template_title = models.CharField(max_length=255, null=True, blank=True)
    template_content = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Template#{self.id} of {self.user_id}"
