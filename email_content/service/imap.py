import imaplib
import email
from email.header import decode_header, make_header
import os
import uuid
import email.utils
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from email_content.models import EmailContent
from email_account.models import EmailAccount
from email_attachment.models import Attachment
from email_metadata.models import EmailMetadata
from email_content.utils import get_imap_config
from utils.spam_filter import classify_emails_in_batch


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


def decode_mime_header(header_string):
    """MIME 인코딩된 이메일 헤더를 디코딩하여 단일 문자열로 반환합니다."""
    if not header_string:
        return ""

    decoded_parts = []
    try:
        decoded_items = decode_header(header_string)
        for item in decoded_items:
            # decode_header는 (bytes, charset) 또는 (str, None) 튜플 리스트를 반환
            if not isinstance(item, tuple):
                decoded_parts.append(str(item))
                continue
            
            # 튜플의 길이가 2가 아닌 경우 처리
            if len(item) != 2:
                print(f"[DECODE WARNING] Unexpected item format: {item}")
                decoded_parts.append(str(item[0]) if item else "")
                continue
                
            part, charset = item
                
            if isinstance(part, bytes):
                # 비표준 Charset(e.g., 'utf-8*ja') 수용을 위한 정리
                cleaned_charset = (charset or "utf-8").split("*")[0].strip()
                try:
                    decoded_parts.append(part.decode(cleaned_charset, "ignore"))
                except LookupError:  # 알 수 없는 인코딩일 경우 fallback
                    decoded_parts.append(part.decode("utf-8", "ignore"))
            else:
                decoded_parts.append(str(part) if part else "")
    except Exception as e:
        print(f"[DECODE ERROR] Failed to decode header '{header_string[:100]}': {e}")
        # fallback: 원본 문자열 반환
        return str(header_string)

    return "".join(decoded_parts) if decoded_parts else ""


def parse_addresses(header_string):
    """
    주소 헤더 문자열을 파싱하여, MIME 인코딩된 이름을 디코딩하고,
    "이름 <주소>" 형식의 문자열 리스트로 반환합니다.
    """
    if not header_string:
        return []

    addr_tuples = email.utils.getaddresses([header_string])
    decoded_addrs = []

    for name, addr in addr_tuples:
        try:
            decoded_name_parts = []
            decoded_items = decode_header(name)
            for item in decoded_items:
                if not isinstance(item, tuple):
                    decoded_name_parts.append(str(item))
                    continue
                
                if len(item) != 2:
                    decoded_name_parts.append(str(item[0]) if item else "")
                    continue
                    
                part, charset = item
                    
                if isinstance(part, bytes):
                    # 비표준 Charset(e.g., 'utf-8*ja') 수용을 위한 정리
                    cleaned_charset = (charset or "utf-8").split("*")[0]
                    decoded_name_parts.append(part.decode(cleaned_charset, "ignore"))
                else:
                    decoded_name_parts.append(str(part) if part else "")
            decoded_name = "".join(decoded_name_parts).strip()
        except Exception:
            decoded_name = name.strip()

        # formataddr()의 재인코딩을 피하기 위해 수동으로 문자열 조합
        if decoded_name and addr:
            decoded_addrs.append(f"{decoded_name} <{addr}>")
        elif addr:
            decoded_addrs.append(addr)
        elif decoded_name:
            decoded_addrs.append(decoded_name)

    return decoded_addrs


def fetch_and_store_emails(address):
    """
    메모리 효율적인 방식으로 이메일을 동기화합니다.
    1. 마지막 동기화 시간 이후의 새 메일만 조회합니다.
    2. 첨부파일은 즉시 디스크에 저장하여 메모리 부하를 최소화합니다.
    3. 수집된 메일 본문을 LLM에 일괄 전송하여 스팸 여부를 분류합니다.
    4. 분류 결과와 함께 이메일 및 관련 데이터를 DB에 저장합니다.
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
    except Exception as e:
        raise ValueError(f"IMAP 연결 또는 로그인 실패: {e}")

    try:
        # 3. UID 조회 최적화
        search_criteria = "ALL"
        sync_start_date = account.last_synced or (datetime.now() - timedelta(days=7))
        search_date = (sync_start_date - timedelta(days=1)).strftime("%d-%b-%Y")
        search_criteria = f'(SENTSINCE "{search_date}")'
        
        print(f"[SYNC DEBUG] Account: {account.address}")
        print(f"[SYNC DEBUG] Search date: {search_date}")
        print(f"[SYNC DEBUG] Search criteria: {search_criteria}")

        status, data = imap.search(None, search_criteria)
        if status != "OK":
            all_uids = []
        else:
            all_uids = data[0].split()
        
        print(f"[SYNC DEBUG] Total UIDs found: {len(all_uids)}")

        uids_to_process = all_uids[-100:]  # 한 번에 최대 100개
        print(f"[SYNC DEBUG] UIDs to process: {len(uids_to_process)}")

        # 이미 DB에 있는 UID는 건너뛰기
        if uids_to_process:
            existing_uids = set(
                EmailMetadata.objects.filter(
                    account=account, uid__in=[uid.decode() for uid in uids_to_process]
                ).values_list("uid", flat=True)
            )
            uids_to_fetch = [uid for uid in uids_to_process if uid.decode() not in existing_uids]
        else:
            uids_to_fetch = []
        
        print(f"[SYNC DEBUG] Existing UIDs in DB: {len(existing_uids) if uids_to_process else 0}")
        print(f"[SYNC DEBUG] New UIDs to fetch: {len(uids_to_fetch)}")

        if not uids_to_fetch:
            account.last_synced = datetime.now()
            account.save(update_fields=["last_synced"])
            return

        # 4. 데이터 분리 수집 (1차 루프)
        emails_for_llm = []
        processed_email_data = {}
        
        print(f"[SYNC DEBUG] Starting to fetch {len(uids_to_fetch)} emails...")

        for uid in uids_to_fetch:
            try:
                status, msg_data = imap.fetch(uid, "(RFC822)")
                if status != "OK":
                    print(f"[SYNC DEBUG] Failed to fetch UID {uid.decode()}")
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                text_body, html_body = None, None
                attachments_info = []

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        disp = str(part.get("Content-Disposition"))

                        try:
                            charset = part.get_content_charset() or "utf-8"
                            if "attachment" not in disp:
                                if ctype == "text/plain":
                                    text_body = part.get_payload(decode=True).decode(charset, errors="ignore")
                                elif ctype == "text/html":
                                    html_body = part.get_payload(decode=True).decode(charset, errors="ignore")

                            if "attachment" in disp and part.get_filename():
                                file_bytes = part.get_payload(decode=True)
                                filename = decode_mime_header(part.get_filename())
                                if file_bytes:
                                    local_path = save_attachment_locally(file_bytes, filename)
                                    attachments_info.append(
                                        {
                                            "filename": filename,
                                            "mime_type": ctype,
                                            "size": len(file_bytes),
                                            "path": local_path,
                                        }
                                    )
                        except Exception:
                            continue  # 개별 파트 오류는 무시
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    if msg.get_content_type() == "text/plain":
                        text_body = msg.get_payload(decode=True).decode(charset, errors="ignore")
                    elif msg.get_content_type() == "text/html":
                        html_body = msg.get_payload(decode=True).decode(charset, errors="ignore")

                uid_str = uid.decode()
                
                try:
                    subject = decode_mime_header(msg.get("Subject", ""))
                except Exception as e:
                    print(f"[ERROR] Subject decode failed for UID {uid_str}: {e}")
                    raise

                try:
                    parsed_date = email.utils.parsedate_to_datetime(msg.get("Date", ""))
                except Exception:
                    parsed_date = datetime.now()

                emails_for_llm.append({"id": uid_str, "subject": subject, "body": text_body or html_body or ""})

                try:
                    from_header = decode_mime_header(msg.get("From", ""))
                except Exception as e:
                    print(f"[ERROR] From decode failed for UID {uid_str}: {e}")
                    raise
                    
                try:
                    to_header = ", ".join(parse_addresses(msg.get("To", "")))
                except Exception as e:
                    print(f"[ERROR] To parse failed for UID {uid_str}: {e}")
                    raise
                    
                try:
                    cc_header = ", ".join(parse_addresses(msg.get("Cc", "")))
                except Exception as e:
                    print(f"[ERROR] Cc parse failed for UID {uid_str}: {e}")
                    raise

                processed_email_data[uid_str] = {
                    "message_id": msg.get("Message-ID"),
                    "gm_msgid": msg.get("X-GM-MSGID") if "gmail" in imap_host else None,
                    "subject": subject,
                    "from_header": from_header,
                    "to_header": to_header,
                    "cc_header": cc_header,
                    "text_body": text_body,
                    "html_body": html_body,
                    "has_attachment": bool(attachments_info),
                    "attachments": attachments_info,
                    "parsed_date": parsed_date,
                }
                print(f"[SYNC DEBUG] Processed email: {subject[:50]}")
            except Exception as e:
                print(f"[SYNC DEBUG] Error processing UID {uid.decode()}: {e}")
                continue  # 개별 이메일 fetch/parse 오류는 무시
        
        print(f"[SYNC DEBUG] Total processed: {len(processed_email_data)} emails")
        print(f"[SYNC DEBUG] Emails for LLM: {len(emails_for_llm)}")        # 5. 스팸 필터 일괄 호출
        classification_results = {}
        if emails_for_llm:
            job = account.job or ""
            usage = account.usage or ""
            interests = account.interests or []
            try:
                print(f"[SYNC DEBUG] Calling spam filter for {len(emails_for_llm)} emails...")
                classification_results = classify_emails_in_batch(
                    emails=emails_for_llm, job=job, usage=usage, interests=interests
                )
                print(f"[SYNC DEBUG] Spam filter completed. Results: {classification_results}")
            except Exception as e:
                print(f"[SYNC DEBUG] Spam filter ERROR: {e}")
                # 스팸 필터 실패 시 모두 inbox로 처리
                classification_results = {email["id"]: "inbox" for email in emails_for_llm}

        # 6. DB에 저장 (2차 루프)
        for uid_str, data in processed_email_data.items():
            with transaction.atomic():
                classification = classification_results.get(uid_str, "inbox")
                is_spammed = classification == "spam"

                email_obj = EmailContent.objects.create(
                    message_id=data["message_id"],
                    subject=data["subject"],
                    from_header=data["from_header"],
                    to_header=data["to_header"],
                    cc_header=data["cc_header"],
                    text_body=data["text_body"],
                    html_body=data["html_body"],
                    has_attachment=data["has_attachment"],
                    date=data["parsed_date"],
                    gm_msgid=data.get("gm_msgid"),
                )

                EmailMetadata.objects.create(
                    account=account,
                    email=email_obj,
                    uid=uid_str,
                    folder="spam" if is_spammed else "inbox",
                    is_spammed=is_spammed,
                    received_at=data["parsed_date"],
                )

                for att_info in data["attachments"]:
                    Attachment.objects.create(
                        email=email_obj,
                        file_name=att_info["filename"],
                        mime_type=att_info["mime_type"],
                        file_size=att_info["size"],
                        file_path=att_info["path"],
                    )

        # 마지막 동기화 시간 업데이트
        account.last_synced = datetime.now()
        account.save(update_fields=["last_synced"])

    finally:
        imap.close()
        imap.logout()
