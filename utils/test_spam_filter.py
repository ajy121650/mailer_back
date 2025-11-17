"""
utils/spam_filter.py의 classify_emails_in_batch 함수를 테스트합니다.

실행 방법:
    python utils/test_spam_filter.py

필수 조건:
    - .env 파일에 GOOGLE_API_KEY가 설정되어 있어야 합니다.
    - 필요한 패키지: langchain-google-genai, langgraph, python-dotenv
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가 (Django 없이 실행하기 위해)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.spam_filter import classify_emails_in_batch


def test_classify_emails_in_batch():
    """샘플 이메일로 classify_emails_in_batch 함수를 테스트합니다."""

    # 테스트용 샘플 이메일 데이터
    sample_emails = [
        {
            "id": "1",
            "subject": "Congratulations! You won $1,000,000!",
            "body": "Click here to claim your prize now! Limited time offer. Act fast!",
        },
        {
            "id": "2",
            "subject": "Project Update - Q4 Roadmap",
            "body": "Hi team, attached is the Q4 roadmap document. Please review and share your feedback by Friday.",
        },
        {
            "id": "3",
            "subject": "RE: Python Django Best Practices",
            "body": "Thanks for the article! I found the section on middleware really helpful. Let's discuss this in our next code review.",
        },
        {
            "id": "4",
            "subject": "URGENT: Your account will be suspended",
            "body": "Your account has suspicious activity. Click this link immediately to verify your identity or your account will be deleted.",
        },
        {
            "id": "5",
            "subject": "Weekly Newsletter: AI and Machine Learning",
            "body": "This week's top stories: New breakthrough in LLM efficiency, practical guide to fine-tuning, and upcoming conferences.",
        },
    ]

    # 사용자 프로필 설정
    user_job = "Software Engineer"
    user_interests = ["Python", "Django", "Machine Learning", "Web Development"]
    user_usage = "Work and personal development"

    print("=" * 80)
    print("🧪 Testing classify_emails_in_batch")
    print("=" * 80)
    print(f"\n📧 Processing {len(sample_emails)} emails...")
    print("👤 User Profile:")
    print(f"   - Job: {user_job}")
    print(f"   - Interests: {', '.join(user_interests)}")
    print(f"   - Usage: {user_usage}")
    print("\n" + "=" * 80)

    try:
        # classify_emails_in_batch 함수 호출
        result = classify_emails_in_batch(
            emails=sample_emails, job=user_job, interests=user_interests, usage=user_usage
        )

        print("\n✅ Classification Results:")
        print("=" * 80)

        if not result:
            print("⚠️  No results returned. Check for errors in the function.")
            return

        # 결과 출력
        spam_count = 0
        inbox_count = 0

        for email in sample_emails:
            email_id = email["id"]
            classification = result.get(email_id, "UNKNOWN")

            if classification == "spam":
                spam_count += 1
                emoji = "🚫"
            elif classification == "inbox":
                inbox_count += 1
                emoji = "✉️"
            else:
                emoji = "❓"

            print(f"\n{emoji} [{classification.upper()}] {email_id}")
            print(f"   Subject: {email['subject']}")
            print(f"   Body: {email['body'][:80]}...")

        print("\n" + "=" * 80)
        print("📊 Summary:")
        print(f"   - Total: {len(sample_emails)}")
        print(f"   - Inbox: {inbox_count}")
        print(f"   - Spam: {spam_count}")
        print(f"   - Unknown: {len(sample_emails) - inbox_count - spam_count}")
        print("=" * 80)

        # 검증
        if inbox_count + spam_count == len(sample_emails):
            print("\n✅ All emails were classified successfully!")
        else:
            print("\n⚠️  Some emails were not classified properly.")

    except Exception as e:
        print(f"\n❌ Error occurred: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return


def test_empty_emails():
    """빈 이메일 리스트로 테스트합니다."""
    print("\n" + "=" * 80)
    print("🧪 Testing with empty email list")
    print("=" * 80)

    try:
        result = classify_emails_in_batch(emails=[], job="Developer", interests=["Python"], usage="Work")
        print(f"✅ Result for empty list: {result}")
    except Exception as e:
        print(f"❌ Error with empty list: {type(e).__name__}: {e}")


def test_single_email():
    """단일 이메일로 테스트합니다."""
    print("\n" + "=" * 80)
    print("🧪 Testing with single email")
    print("=" * 80)

    single_email = [
        {
            "id": "test_001",
            "subject": "Test Email",
            "body": "This is a test email to check if the function works with a single input.",
        }
    ]

    try:
        result = classify_emails_in_batch(
            emails=single_email, job="Tester", interests=["Testing", "Quality Assurance"], usage="Work"
        )
        print(f"✅ Single email result: {result}")
    except Exception as e:
        print(f"❌ Error with single email: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # 환경 변수 확인
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables.")
        print("Please create a .env file with your Google API key:")
        print("   GOOGLE_API_KEY=your_api_key_here")
        sys.exit(1)

    print(f"✅ GOOGLE_API_KEY found: {api_key[:10]}...{api_key[-4:]}")

    # 메인 테스트 실행 (주의: API quota 제한으로 인해 한 번에 하나씩 실행하는 것이 좋습니다)
    test_classify_emails_in_batch()

    # 추가 테스트 (선택적 - quota를 고려하여 주석 처리)
    # test_empty_emails()
    # test_single_email()

    print("\n" + "=" * 80)
    print("🎉 Test completed!")
    print("=" * 80)
    print("\n💡 Tip: Gemini API free tier has rate limits (2 requests/min for gemini-2.5-pro).")
    print("   If you need to run multiple tests, wait 1 minute between runs or use gemini-2.0-flash-exp.")
