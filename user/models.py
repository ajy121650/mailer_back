from django.db import models


# Create your models here.
class User(models.Model):
    user_id = models.CharField(max_length=255, unique=True)  # clerk 같은 외부 ID

    def __str__(self):
        return self.user_id

    @property
    def is_authenticated(self):
        """
        DRF/Django의 인증 시스템을 위한 속성입니다.
        이 객체가 반환되면 항상 인증된 것으로 간주합니다.
        """
        return True

    @property
    def is_anonymous(self):
        """
        DRF/Django의 인증 시스템을 위한 속성입니다.
        이 객체는 익명 사용자가 아닙니다.
        """
        return False
