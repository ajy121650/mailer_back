from django.apps import AppConfig


class EmailMetadataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "email_metadata"

    def ready(self):
        # 시그널을 등록합니다.
        pass
