import imaplib
import email
from .models import EmailContent
from email_account.models import EmailAccount
from email_attachment.models import Attachment
from email_metadata.models import EmailMetadata
from .utils import get_imap_config
import uuid
import boto3
import email.utils


# S3 클라이언트
s3 = boto3.client("s3")
BUCKET_NAME = "my-mailbox-storage"


def upload_to_s3(file_bytes, prefix, ext):
    file_key = f"{prefix}/{uuid.uuid4()}.{ext}"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_key, Body=file_bytes)
    return f"s3://{BUCKET_NAME}/{file_key}"


def parse_addresses(header):
    if not header:
        return []
    return [addr.strip() for addr in header.split(",")]


def fetch_and_store_emails(address):
    """
    1. EmailAccount 조회
    2. IMAP 로그인 → 최근 50개 메일
    3. Email + EmailMetadata + Attachment 저장
    """
    # 1. 계정 조회
    account = EmailAccount.objects.filter(address=address).first()
    if not account:
        raise ValueError("해당 계정이 존재하지 않습니다.")

    # 2. IMAP 연결
    try:
        imap_config = get_imap_config(account.domain)
        imap_host = imap_config["host"]
        imap_port = imap_config["port"]
        # 필요하다면 ssl 옵션도 imap_config["ssl"]로 사용 가능

        imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        imap.login(account.address, account.email_password)
        imap.select("INBOX")
    except imaplib.IMAP4.error as e:
        # 인증 실패, 서버 오류 등 IMAP 관련 에러 처리
        raise ValueError(f"IMAP 연결 또는 로그인 실패: {e}")
    except Exception as e:
        # 기타 예외 처리
        raise ValueError(f"이메일 서버 연결 중 알 수 없는 오류: {e}")

    # 3. 최근 50개 UID 가져오기
    status, data = imap.search(None, "ALL")
    all_uids = data[0].split()
    recent_uids = all_uids[-50:] if len(all_uids) > 50 else all_uids

    for uid in recent_uids:
        status, msg_data = imap.fetch(uid, "(RFC822)")
        raw_msg = msg_data[0][1]
        msg = email.message_from_bytes(raw_msg)

        message_id = msg.get("Message-ID")
        gm_msgid = None

        if imap_host == "imap.gmail.com":
            gm_msgid = msg.get("X-GM-MSGID")

        # 중복 스킵 로직
        if imap_host == "imap.gmail.com":
            # Gmail은 gm_msgid를 사용해서 중복 체크
            if EmailContent.objects.filter(gm_msgid=gm_msgid).exists():
                continue
        else:
            # 그 외는 message_id로만 중복 체크
            if EmailContent.objects.filter(message_id=message_id).exists():
                continue

        subject = msg.get("Subject", "")
        from_header = msg.get("From", "")
        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        bcc_header = msg.get("Bcc", "")
        date = msg.get("Date", "")
        # date 파싱
        try:
            parsed_date = email.utils.parsedate_to_datetime(date)
        except Exception:
            parsed_date = None

        # 본문 추출
        text_body, html_body = None, None
        has_attachment = False
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    text_body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                elif ctype == "text/html" and "attachment" not in disp:
                    html_body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                elif part.get_content_disposition() == "attachment":
                    has_attachment = True
        else:
            if msg.get_content_type() == "text/plain":
                text_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
            elif msg.get_content_type() == "text/html":
                html_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")

        # JSONField에 맞게 주소 파싱
        to_header_json = parse_addresses(to_header)
        cc_header_json = parse_addresses(cc_header)
        bcc_header_json = parse_addresses(bcc_header)

        # 5. EmailContent 저장
        email_obj = EmailContent.objects.create(
            message_id=message_id,
            gm_msgid=gm_msgid,
            subject=subject,
            from_header=from_header,
            to_header=to_header_json,
            cc_header=cc_header_json,
            bcc_header=bcc_header_json,
            text_body=text_body,
            html_body=html_body,
            has_attachment=has_attachment,
            date=parsed_date,
        )

        # 6. EmailMetadata 저장
        EmailMetadata.objects.create(
            account=account,
            email=email_obj,
            uid=uid.decode() if isinstance(uid, bytes) else str(uid),
            folder="inbox",  # 기본값, 필요시 로직 추가
            received_at=parsed_date,
            # 기타 필드는 기본값 사용
        )

        # 7. 첨부파일 저장
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                file_bytes = part.get_payload(decode=True)
                s3_path = upload_to_s3(file_bytes, prefix="attachments", ext="bin")
                Attachment.objects.create(
                    email=email_obj,
                    filename=filename,
                    content_type=part.get_content_type(),
                    size=len(file_bytes),
                    s3_path=s3_path,
                )

    imap.close()
    imap.logout()
