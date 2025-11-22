from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import EmailMetadata

# 정합성을 유지한 이메일 삭제를 위해 구성한 시그널 핸들러.


@receiver(post_delete, sender=EmailMetadata)
def handle_email_content_deletion(sender, instance, **kwargs):
    """
    EmailMetadata가 삭제된 후, 연결된 EmailContent를 참조하는 다른 EmailMetadata가
    없다면 해당 EmailContent를 삭제합니다.
    """
    # 삭제된 EmailMetadata 인스턴스에서 EmailContent 객체를 가져옵니다.
    email_content = instance.email

    # email_content가 존재하고, 이를 참조하는 다른 EmailMetadata가 없는지 확인합니다.
    # transaction.atomic으로 감싸서 확인과 삭제 로직이 분리되지 않고 한 번에 실행되도록 보장합니다.
    if email_content:
        with transaction.atomic():
            # EmailContent에 연결된 EmailMetadata의 수를 확인합니다.
            # related_name="metadata"를 사용합니다.
            if email_content.metadata.count() == 0:
                # 참조가 하나도 없으면 EmailContent를 삭제합니다.
                email_content.delete()
