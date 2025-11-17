import os
import django
from dotenv import load_dotenv
from user.models import User
from email_account.models import EmailAccount
from email_content.utils import get_imap_config

# --- Django Setup ---
# PWD: /home/dongi/mailer_back
# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Setup Django
django.setup()
# --- End Django Setup ---


def main():
    """
    테스트용 사용자 및 이메일 계정을 생성하고 설정합니다.
    - .env 파일에서 환경 변수를 로드합니다.
    - 'testuser'라는 ID를 가진 사용자를 생성하거나 가져옵니다.
    - .env에 지정된 이메일 주소와 비밀번호로 EmailAccount를 생성하거나 업데이트합니다.
    """
    print("--- 테스트 설정 시작 ---")

    # .env 파일에서 환경 변수 로드
    load_dotenv()

    # 테스트용 사용자 정보
    test_user_id = "testuser"

    # 1. 테스트용 사용자 생성 (없으면 생성)
    user, created = User.objects.get_or_create(user_id=test_user_id)
    if created:
        print(f"테스트 사용자 '{user.user_id}'가 생성되었습니다.")
    else:
        print(f"테스트 사용자 '{user.user_id}'가 이미 존재합니다.")

    # .env에서 이메일 정보 가져오기
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not email_address or not email_password:
        print("오류: .env 파일에 EMAIL_ADDRESS 또는 EMAIL_PASSWORD가 설정되지 않았습니다.")
        print("스크립트를 종료합니다.")
        return

    # 2. EmailAccount 등록 (없으면 생성, 있으면 업데이트)
    try:
        # 'user@gmail.com' -> 'gmail.com' -> 'gmail'
        full_domain = email_address.split("@")[1]
        simple_domain = full_domain.split(".")[0].lower()
        imap_config = get_imap_config(simple_domain)
        imap_host = imap_config["host"]
    except (IndexError, AttributeError):
        print(f"오류: 유효하지 않은 이메일 주소 형식입니다: {email_address}")
        return
    except ValueError as e:
        print(f"오류: {e}")
        return

    # update_or_create를 사용하여 사용자, 도메인 등 기본 정보를 업데이트/생성합니다.
    email_account, created = EmailAccount.objects.update_or_create(
        address=email_address,
        defaults={
            "user": user,
            "domain": imap_host,  # 올바른 IMAP 호스트 주소 사용
            "is_valid": True,
            "job": "컴퓨터 공학과 학생",
            "usage": "공부용",
            "interests": [
                "프로그래밍",
                "자료구조",
                "알고리즘",
                "운영체제",
                "네트워크",
                "인공지능",
            ],
        },
    )

    # .env 파일의 비밀번호가 최신 정보이므로 항상 암호화하여 저장합니다.
    email_account.email_password = email_password
    email_account.save()

    if created:
        print(f"이메일 계정 '{email_account.address}'가 생성되고 '{user.user_id}' 사용자에게 연결되었습니다.")
    else:
        print(f"이메일 계정 '{email_account.address}'의 정보가 업데이트되었습니다.")

    print("--- 테스트 설정 완료 ---")


if __name__ == "__main__":
    main()
