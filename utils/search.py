import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv

load_dotenv()

# ===== 사용자 계정 정보 =====
EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"  # 네이버: imap.naver.com, Gmail: imap.gmail.com, Outlook: outlook.office365.com
IMAP_PORT = 993  # SSL 포트
# ===== 1. 서버 연결 =====
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
# ===== 2. 로그인 =====
mail.login(EMAIL, PASSWORD)
print(":흰색_확인_표시: 로그인 성공")
# ===== 3. 메일함 선택 =====
mail.select("INBOX")  # 받은편지함
# ===== 4. 메일 검색 (최근 5개만) =====
status, data = mail.search(None, "ALL")
if status != "OK":
    print("메일 검색 실패")
else:
    mail_ids = data[0].split()
    latest_ids = mail_ids[-5:]  # 최근 5개 UID
    for num in latest_ids:
        status, msg_data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue
        raw_msg = msg_data[0][1]
        msg = email.message_from_bytes(raw_msg)
        # 제목 디코딩
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")
        from_ = msg.get("From")
        date_ = msg.get("Date")
        print("=" * 50)
        print(f":이메일: 제목: {subject}")
        print(f":상반신_그림자: 보낸사람: {from_}")
        print(f":날짜: 날짜: {date_}")
# ===== 5. 연결 종료 =====
mail.logout()
print(":흰색_확인_표시: 로그아웃")
