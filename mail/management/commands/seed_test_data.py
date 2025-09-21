import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps

# 임의의 시간 세팅용 패키지.
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test data for the mailer application"

    def handle(self, *args, **kwargs):
        # Django의 앱 시스템을 통해 모델을 안전하게 가져옵니다.
        EmailAccount = apps.get_model("user", "EmailAccount")
        Email = apps.get_model("mail", "Email")
        Mailbox = apps.get_model("mail", "Mailbox")
        EmailRecipient = apps.get_model("mail", "EmailRecipient")

        self.stdout.write(self.style.SUCCESS("Seeding database with test data..."))

        # 1. 테스트 유저 생성
        test_user, created = User.objects.get_or_create(username="testuser", defaults={"password": "testpassword123"})
        if created:
            test_user.set_password("testpassword123")
            test_user.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created user: {test_user.username}"))
        else:
            self.stdout.write(self.style.WARNING(f"User {test_user.username} already exists."))

        # 2. 테스트 이메일 계정 3개 생성
        email_accounts_to_create = [
            "test1@example.com",
            "test2@example.com",
            "test3@example.com",
        ]
        email_accounts = []
        for email_address in email_accounts_to_create:
            account, created = EmailAccount.objects.get_or_create(user=test_user, email_address=email_address)
            email_accounts.append(account)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  - Created email account: {email_address}"))
            else:
                self.stdout.write(self.style.WARNING(f"  - Email account {email_address} already exists."))

        # 3. 각 계정당 20개의 테스트 이메일 생성
        self.stdout.write(self.style.SUCCESS("Creating emails..."))
        folder_choices = [choice[0] for choice in Mailbox.FolderType.choices]

        for account in email_accounts:
            self.stdout.write(f"  - For account: {account.email_address}")
            for i in range(20):
                folder = random.choice(folder_choices)

                from_addr = ""
                to_addr = ""

                # 'sent' 폴더일 경우 from_address와 to_address를 재설정
                if folder == "sent":
                    from_addr = account.email_address
                    to_addr = f"recipient{i + 1}@{random.choice(['example.com', 'test.com', 'mailer.com'])}"
                else:
                    from_addr = f"sender{i + 1}@{random.choice(['example.com', 'test.com', 'mailer.com'])}"
                    to_addr = account.email_address

                # Email 객체 생성
                email = Email.objects.create(
                    subject=f"Test Subject {i + 1} for {account.email_address}",
                    from_address=from_addr,
                    body=f"This is the body of test email {i + 1}.",
                    sent_at=timezone.now() - timedelta(days=i, hours=i * 2),
                )

                # EmailRecipient 객체 생성
                EmailRecipient.objects.create(email=email, recipient_address=to_addr, recipient_type="TO")

                # 'sent'가 아닌 메일에만 참조 추가
                if folder != "sent" and i % 2 == 0:
                    other_recipients = [acc.email_address for acc in email_accounts if acc != account]
                    if other_recipients:
                        EmailRecipient.objects.create(
                            email=email,
                            recipient_address=random.choice(other_recipients),
                            recipient_type="CC",
                        )

                # Mailbox 객체 생성
                Mailbox.objects.create(
                    account=account,
                    email=email,
                    folder=folder,
                    is_read=random.choice([True, False]),
                    is_important=random.choice([True, False]),
                )
            self.stdout.write(self.style.SUCCESS("    -> Created 20 emails with recipients and sent_at."))

        self.stdout.write(self.style.SUCCESS("Database seeding complete!"))
