import imaplib
import email
from email.header import decode_header
import os

######################테스트용 코드##################
from dotenv import load_dotenv

# 새로 만든 스팸 필터 함수를 임포트합니다.
from spam_filter import classify_emails_in_batch

###################################################


def run_test():
    """
    이메일을 가져와 새로 만든 배치 분류 함수를 테스트합니다.
    """
    ####################테스트용 변수#################
    load_dotenv()
    ################################################
    # --- 1. 이메일 서버 연결 및 로그인 ---
    EMAIL = os.getenv("EMAIL_ADDRESS")
    PASSWORD = os.getenv("EMAIL_PASSWORD")
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    print("--- 1. 이메일 서버에 로그인하여 최근 20개 이메일을 가져옵니다... ---")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, PASSWORD)
        mail.select("INBOX")
    except Exception as e:
        print(f"오류: 이메일 서버 연결/로그인 실패. ({e})")
        return

    status, data = mail.search(None, "ALL")
    if status != "OK":
        print("오류: 이메일 검색 실패.")
        mail.logout()
        return

    # --- 2. 이메일 데이터를 LLM에 보낼 형식으로 준비 ---
    print("--- 2. 이메일 데이터를 API 요청 형식에 맞게 준비합니다... ---")
    emails_to_classify = []
    mail_ids = data[0].split()
    latest_ids = mail_ids[-20:]

    for num in reversed(latest_ids):
        status, msg_data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])

        decoded_subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(decoded_subject, bytes):
            subject = decoded_subject.decode(encoding or "utf-8", errors="ignore")
        else:
            subject = str(decoded_subject)

        from_ = str(msg.get("From"))

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="ignore"
                        )
                        break
                    except Exception:
                        continue
        else:
            if msg.get_content_type() == "text/plain":
                try:
                    body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    pass

        content_for_llm = f"Subject: {subject}\n\nBody: {body}"
        content_for_llm = content_for_llm[:2000]

        emails_to_classify.append({"id": num.decode(), "subject": subject, "from": from_, "body": content_for_llm})

    mail.logout()

    # --- 3. 스팸 일괄 분류 요청 ---
    print("--- 3. LLM에 스팸 분류를 일괄 요청합니다... (시간이 걸릴 수 있습니다) ---")
    user_likes = ["코딩", "AI", "대학교"]
    user_dislikes = ["게임"]

    # API에 전달할 데이터에는 body만 포함 (토큰 절약)
    api_payload = [{"id": e["id"], "subject": e["subject"], "body": e["body"]} for e in emails_to_classify]
    classification_results = classify_emails_in_batch(api_payload, user_likes, user_dislikes)

    if not classification_results:
        print("오류: 스팸 분류에 실패했습니다.")
        return

    # --- 4. 최종 결과 출력 및 파일 저장 ---
    print("\n--- 최종 분류 결과 ---")
    final_output_lines = []
    for email_data in emails_to_classify:
        email_id = email_data["id"]
        classification = classification_results.get(email_id, "분류 실패")

        output_str = (
            f"==================== ID: {email_id} ====================\n"
            f"  - 제목: {email_data['subject']}\n"
            f"  - 발신자: {email_data['from']}\n"
            f"  - 내용 미리보기: {email_data['body'][:100].strip()}...\n"
            f"  - 최종 판정: {classification.upper()}\n"
        )
        print(output_str)
        final_output_lines.append(output_str)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = os.path.join(script_dir, "classification_results.txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(final_output_lines))

    print(f"\n--- 완료! 결과가 {output_filename} 파일에 저장되었습니다. ---")


if __name__ == "__main__":
    run_test()
