from django.db import models


# Create your models here.
class User(models.Model):
    user_id = models.CharField(max_length=255, unique=True)  # clerk 같은 외부 ID
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.user_id
