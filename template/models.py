from django.db import models
from user.models import User
from email_account.models import EmailAccount


## !!!!!!!! 경고 !!!!!!!!!!!!!
## Template 모델 아직 migrate 안 했음. 기획 확정 되고 model 확정 된 이후에 migrate 할 것!!!!!!!!!!!


# Create your models here.
class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="templates")
    email_account = models.ForeignKey(
        EmailAccount, on_delete=models.CASCADE, related_name="templates", null=True, blank=True
    )
    template_content = models.CharField(max_length=1000, default="", null=True, blank=True)
    template_title = models.CharField(max_length=255, default="", null=True, blank=True)
    main_category = models.CharField(max_length=100, default="", null=True, blank=True)
    sub_category = models.CharField(max_length=100, default="", null=True, blank=True)
    topic = models.CharField(max_length=100, default="", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Template#{self.id} of {self.email_account.address}"
