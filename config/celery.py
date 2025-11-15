# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("Mailer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# 권장 옵션
app.conf.timezone = "Asia/Seoul"
app.conf.task_ignore_result = True  # 결과 저장 필요 없으면
