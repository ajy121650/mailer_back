import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps

# 임의의 시간 세팅용 패키지.
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test data for the mailer application'

    def handle(self, *args, **kwargs):
        # Django의 앱 시스템을 통해 모델을 안전하게 가져옵니다.
        EmailAccount = apps.get_model('user', 'EmailAccount')
        Email = apps.get_model('mail', 'Email')
        Mailbox = apps.get_model('mail', 'Mailbox')
        EmailRecipient = apps.get_model('mail', 'EmailRecipient')

        self.stdout.write(self.style.SUCCESS('Seeding database with test data...'))

        # 1. 테스트 유저 생성
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'password': 'testpassword123'}
        )
        if created:
            test_user.set_password('testpassword123')
            test_user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully created user: {test_user.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {test_user.username} already exists.'))

        # 2. 테스트 이메일 계정 3개 생성
        email_accounts_to_create = ['test1@example.com', 'test2@example.com', 'test3@example.com']
        email_accounts = []
        for email_address in email_accounts_to_create:
            account, created = EmailAccount.objects.get_or_create(
                user=test_user,
                email_address=email_address
            )
            email_accounts.append(account)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  - Created email account: {email_address}'))
            else:
                self.stdout.write(self.style.WARNING(f'  - Email account {email_address} already exists.'))

        # 3. 각 계정당 20개의 테스트 이메일 생성
        self.stdout.write(self.style.SUCCESS('Creating emails...'))
        folder_choices = [choice[0] for choice in Mailbox.FolderType.choices]

        for account in email_accounts:
            self.stdout.write(f'  - For account: {account.email_address}')
            for i in range(20):
                # Email 객체 생성 (sent_at 추가)
                email = Email.objects.create(
                    subject=f'Test Subject {i+1} for {account.email_address}',
                    from_address=f'sender{i+1}@example.com',
                    body=f'This is the body of test email {i+1}.',
                    sent_at=timezone.now() - timedelta(days=i, hours=i*2)
                )

                # EmailRecipient 객체 생성 (수신자 정보 추가)
                # 1. 받는 사람 (TO) - 자기 자신
                EmailRecipient.objects.create(
                    email=email,
                    recipient_address=account.email_address,
                    recipient_type='TO'
                )
                # 2. 참조 (CC) - 다른 테스트 계정 중 랜덤
                if i % 2 == 0: # 2번에 1번 꼴로 참조 추가
                    other_recipients = [acc.email_address for acc in email_accounts if acc != account]
                    EmailRecipient.objects.create(
                        email=email,
                        recipient_address=random.choice(other_recipients),
                        recipient_type='CC'
                    )

                # Mailbox 객체 생성 (Email과 EmailAccount 연결)
                Mailbox.objects.create(
                    account=account,
                    email=email,
                    folder=random.choice(folder_choices),
                    is_read=random.choice([True, False]),
                    is_important=random.choice([True, False]),
                )
            self.stdout.write(self.style.SUCCESS(f'    -> Created 20 emails with recipients and sent_at.'))

        self.stdout.write(self.style.SUCCESS('Database seeding complete!'))
