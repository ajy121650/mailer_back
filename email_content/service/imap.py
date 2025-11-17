import imaplib
import email
from email_content.models import EmailContent
from email_account.models import EmailAccount
from email_attachment.models import Attachment
from email_metadata.models import EmailMetadata
from email_content.utils import get_imap_config
import uuid
import email.utils

########## API 테스트를 위해 추가한 import ##########
from django.conf import settings
import os

##################################################

#### 스팸 필터 로직 추가 ####


def save_attachment_locally(file_bytes, original_filename):
    """
    첨부파일을 로컬 파일 시스템에 저장하고, DB에 기록할 상대 경로를 반환합니다.
    """
    # 파일 확장자 추출, 없으면 'bin' 사용
    try:
        ext = original_filename.split(".")[-1] if "." in original_filename else "bin"
    except Exception:
        ext = "bin"

    # 저장 경로 설정 (루트/EmailAttachments/)
    storage_dir = os.path.join(settings.BASE_DIR, "EmailAttachments")
    os.makedirs(storage_dir, exist_ok=True)

    # 고유한 파일명 생성 및 전체 경로 조합
    file_name = f"{uuid.uuid4()}.{ext}"
    relative_path = os.path.join("EmailAttachments", file_name)
    full_path = os.path.join(settings.BASE_DIR, relative_path)

    # 파일 저장
    with open(full_path, "wb") as f:
        f.write(file_bytes)

    # DB에 저장할 상대 경로 반환
    return relative_path


def parse_addresses(header):
    if not header:
        return []
    return [addr.strip() for addr in header.split(",")]


def fetch_and_store_emails(address):
    """
    1. EmailAccount 조회
    2. IMAP 로그인 → 최근 50개 메일
    #### START: 스팸 필터링 로직 추가 ####
    3. 가져온 메일들을 스팸 필터로 일괄 분류
    4. 분류 결과와 함께 Email + EmailMetadata + Attachment 저장
    #### END: 스팸 필터링 로직 추가 ####
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

    #### 스팸 필터링을 위한 데이터 준비 단계 ####
    emails_to_process = []
    for uid in recent_uids:
        status, msg_data = imap.fetch(uid, "(RFC822)")
        raw_msg = msg_data[0][1]
        msg = email.message_from_bytes(raw_msg)

        message_id = msg.get("Message-ID")
        gm_msgid = None

        if imap_host == "imap.gmail.com":
            gm_msgid = msg.get("X-GM-MSGID")

        # 중복 스킵 로직 (EmailMetadata를 통해 계정별로 확인)
        # 이메일이 이미 해당 계정에 대해 저장되었는지 확인
        if imap_host == "imap.gmail.com":
            # Gmail은 gm_msgid를 사용해서 중복 체크
            if EmailMetadata.objects.filter(account=account, email__gm_msgid=gm_msgid).exists():
                continue
        else:
            # 그 외는 message_id로만 중복 체크
            if EmailMetadata.objects.filter(account=account, email__message_id=message_id).exists():
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
        attachments_data = []
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

                if part.get_content_disposition() == "attachment":
                    has_attachment = True
                    attachments_data.append(
                        {
                            "filename": part.get_filename(),
                            "bytes": part.get_payload(decode=True),
                            "content_type": part.get_content_type(),
                        }
                    )
        else:
            if msg.get_content_type() == "text/plain":
                text_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
            elif msg.get_content_type() == "text/html":
                html_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")

        emails_to_process.append(
            {
                "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                "message_id": message_id,
                "gm_msgid": gm_msgid,
                "subject": subject,
                "from_header": from_header,
                "to_header": parse_addresses(to_header),
                "cc_header": parse_addresses(cc_header),
                "bcc_header": parse_addresses(bcc_header),
                "text_body": text_body,
                "html_body": html_body,
                "has_attachment": has_attachment,
                "attachments_data": attachments_data,
                "parsed_date": parsed_date,
            }
        )
    #### 스팸 필터링을 위한 데이터 준비 끝 ####

    #### 스팸 필터링 일괄 호출(불러온 50개에 대해) ####
    # emails_for_classification = [
    #     {"id": e["uid"], "subject": e["subject"], "body": e["text_body"] or ""} for e in emails_to_process
    # ]

    # classification_results = {}
    # if emails_for_classification:
    #     # --- 사용자 선호도 데이터 준비 ---
    #     job_preference = account.job or ""
    #     usage_preference = account.usage or ""
    #     user_preferences = account.interests or {}  # account.interests는 JSONField (dict)
    #     # --- 스팸 필터 일괄 호출 ---
    #     classification_results = classify_emails_in_batch(
    #         emails=emails_for_classification,
    #         job=job_preference,
    #         usage=usage_preference,
    #         interests=user_preferences,
    #     )
    #### END: 스팸 필터 일괄 호출 단계 ####

    #### START: 분류 결과와 함께 DB에 저장하는 단계 ####
    for email_data in emails_to_process:
        # 중복 저장 방지: 계정별 UID, gm_msgid, message_id 기준으로 재확인
        # (상단 fetch 단계에서도 1차 필터링하지만, 저장 직전 2차 확인으로 안전성 강화)
        if EmailMetadata.objects.filter(account=account, uid=email_data["uid"]).exists():
            continue
        if (
            email_data.get("gm_msgid")
            and EmailMetadata.objects.filter(account=account, email__gm_msgid=email_data["gm_msgid"]).exists()
        ):
            continue
        if (
            email_data.get("message_id")
            and EmailMetadata.objects.filter(account=account, email__message_id=email_data["message_id"]).exists()
        ):
            continue
        # classification = classification_results.get(email_data["uid"], "inbox")
        # folder = "spam" if classification == "spam" else "inbox"
        # is_spammed = classification == "spam"

        # 5. EmailContent 저장
        email_obj = EmailContent.objects.create(
            message_id=email_data["message_id"],
            gm_msgid=email_data["gm_msgid"],
            subject=email_data["subject"],
            from_header=email_data["from_header"],
            to_header=email_data["to_header"],
            cc_header=email_data["cc_header"],
            bcc_header=email_data["bcc_header"],
            text_body=email_data["text_body"],
            html_body=email_data["html_body"],
            has_attachment=email_data["has_attachment"],
            date=email_data["parsed_date"],
        )

        # 6. EmailMetadata 저장
        EmailMetadata.objects.create(
            account=account,
            email=email_obj,
            uid=email_data["uid"],
            folder="inbox",  # <-- 스팸 필터 결과 적용
            is_spammed=None,
            received_at=email_data["parsed_date"],
        )

        # 7. 첨부파일 저장
        for att_data in email_data["attachments_data"]:
            file_bytes = att_data.get("bytes")
            original_filename = att_data.get("filename")

            if not file_bytes or not original_filename:
                continue

            # 파일을 로컬에 저장하고 상대 경로를 받음
            local_path = save_attachment_locally(file_bytes, original_filename)

            # Attachment 모델 필드에 맞게 데이터 저장
            Attachment.objects.create(
                email=email_obj,
                file_name=original_filename,
                mime_type=att_data.get("content_type"),
                file_size=len(file_bytes),
                file_path=local_path,
            )
    #### END: 분류 결과와 함께 DB에 저장하는 단계 ####

    imap.close()
    imap.logout()
