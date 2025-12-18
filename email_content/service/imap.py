import imaplib
import email
from email.header import decode_header
import os
import uuid
import email.utils
from datetime import timedelta
import logging

from django.conf import settings
from django.db import transaction

from email_content.models import EmailContent
from email_account.models import EmailAccount
from email_attachment.models import Attachment
from email_metadata.models import EmailMetadata
from email_content.utils import get_imap_config
from utils.spam_filter import classify_emails_in_batch

# Django의 timezone 모듈 임포트 (RuntimeWarning 해결용)
from django.utils import timezone

# 로거 설정
logger = logging.getLogger(__name__)


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
    for part, charset in decode_header(header_string):
        if isinstance(part, bytes):
            # 비표준 Charset(e.g., 'utf-8*ja') 수용을 위한 정리
            cleaned_charset = (charset or "utf-8").split("*")[0].strip()
            try:
                decoded_parts.append(part.decode(cleaned_charset, "ignore"))
            except LookupError:  # 알 수 없는 인코딩일 경우 fallback
                decoded_parts.append(part.decode("utf-8", "ignore"))
        else:
            decoded_parts.append(part)

    return "".join(decoded_parts)


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
            for part, charset in decode_header(name):
                if isinstance(part, bytes):
                    # 비표준 Charset(e.g., 'utf-8*ja') 수용을 위한 정리
                    cleaned_charset = (charset or "utf-8").split("*")[0]
                    decoded_name_parts.append(part.decode(cleaned_charset, "ignore"))
                else:
                    decoded_name_parts.append(part)
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
    메모리 효율적인 방식으로 이메일을 동기화하고, 동기화된 메일 개수를 반환합니다.
    (상세 로깅 추가됨)
    """
    logger.info(f"[{address}] 이메일 동기화 작업을 시작합니다.")
    synced_count = 0

    # 1. 계정 조회
    account = EmailAccount.objects.filter(address=address).first()
    if not account:
        logger.error(f"[{address}] DB에서 계정을 찾을 수 없어 동기화를 중단합니다.")
        raise ValueError("해당 계정이 존재하지 않습니다.")
    logger.info(f"[{address}] DB에서 계정 정보를 성공적으로 조회했습니다.")

    # 2. IMAP 연결
    imap = None
    try:
        imap_config = get_imap_config(account.domain)
        imap_host = imap_config["host"]
        imap_port = imap_config["port"]
        logger.info(f"[{address}] IMAP 서버에 연결을 시도합니다. (Host: {imap_host}, Port: {imap_port})")

        # 타임아웃 30초 설정
        imap = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30)
        imap.login(account.address, account.email_password)
        logger.info(f"[{address}] IMAP 서버 로그인 성공.")

        status, messages = imap.select("INBOX")
        logger.info(f"[{address}] INBOX 선택 결과: status={status}, messages={messages}")
        if status != "OK":
            logger.error(f"[{address}] INBOX 폴더를 열 수 없습니다. (Status: {status})")
            # 연결은 되었으므로 로그아웃은 finally에서 처리
            raise ValueError(f"INBOX 폴더를 열 수 없습니다: {messages}")

    except Exception as e:
        logger.critical(f"[{address}] IMAP 연결 또는 로그인/폴더 선택 실패: {e}", exc_info=True)
        # 여기서 발생한 예외는 상위(View)로 다시 전달
        raise ValueError(f"IMAP 연결 또는 로그인 실패: {e}")

    try:
        # 3. UID 조회 최적화 (하이브리드 방식)
        if account.last_synced:
            # --- 이후 동기화 ---
            sync_start_date = account.last_synced
            search_date = (sync_start_date - timedelta(days=1)).strftime("%d-%b-%Y")
            search_criteria = f'(SENTSINCE "{search_date}")'
            logger.info(f"[{address}] 후속 동기화를 시작합니다. 검색 조건: {search_criteria}")
        else:
            # --- 최초 동기화 ---
            search_criteria = "ALL"
            logger.info(f"[{address}] 최초 동기화를 시작합니다. 모든 메일을 대상으로 합니다.")

        status, data = imap.search(None, search_criteria)
        if status != "OK":
            logger.error(f"[{address}] IMAP search 실패. Status: {status}")
            uids_to_process = []
        else:
            all_uids = data[0].split()
            if not account.last_synced:
                uids_to_process = all_uids[-50:]  # 최초 동기화 시 최신 50개
                logger.info(
                    f"[{address}] 최초 동기화로, 전체 {len(all_uids)}개 중 최신 {len(uids_to_process)}개의 UID를 처리합니다."
                )
            else:
                uids_to_process = all_uids
                logger.info(f"[{address}] 검색된 전체 UID 개수: {len(uids_to_process)}")

        # 이미 DB에 있는 UID는 건너뛰기 (공통 로직)
        if uids_to_process:
            existing_uids = set(
                EmailMetadata.objects.filter(
                    account=account, uid__in=[uid.decode() for uid in uids_to_process]
                ).values_list("uid", flat=True)
            )
            uids_to_fetch = [uid for uid in uids_to_process if uid.decode() not in existing_uids]
            logger.info(
                f"[{address}] 기존에 저장된 UID {len(existing_uids)}개를 제외하고, {len(uids_to_fetch)}개의 새 메일을 가져옵니다."
            )
        else:
            uids_to_fetch = []

        if not uids_to_fetch:
            logger.info(f"[{address}] 가져올 새 메일이 없습니다. 동기화를 종료합니다.")
            account.last_synced = timezone.now()
            account.save(update_fields=["last_synced"])
            return 0  # 동기화된 메일 0개 반환

        # 4. 데이터 분리 수집 (1차 루프)
        emails_for_llm = []
        processed_email_data = {}

        logger.info(f"[{address}] {len(uids_to_fetch)}개 메일에 대한 데이터 수집을 시작합니다.")
        for uid in uids_to_fetch:
            uid_str = uid.decode()
            try:
                status, msg_data = imap.fetch(uid, "(RFC822)")
                if status != "OK":
                    logger.warning(f"[{address}] UID {uid_str} fetch 실패. Status: {status}")
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
                        except Exception as e:
                            logger.warning(f"[{address}] UID {uid_str}의 일부 파트 처리 중 오류: {e}", exc_info=True)
                            continue  # 개별 파트 오류는 무시
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    if msg.get_content_type() == "text/plain":
                        text_body = msg.get_payload(decode=True).decode(charset, errors="ignore")
                    elif msg.get_content_type() == "text/html":
                        html_body = msg.get_payload(decode=True).decode(charset, errors="ignore")

                subject = decode_mime_header(msg.get("Subject", ""))

                try:
                    parsed_date = email.utils.parsedate_to_datetime(msg.get("Date", ""))
                except Exception:
                    parsed_date = timezone.now()

                emails_for_llm.append({"id": uid_str, "subject": subject, "body": text_body or html_body or ""})

                processed_email_data[uid_str] = {
                    "message_id": msg.get("Message-ID"),
                    "gm_msgid": msg.get("X-GM-MSGID") if "gmail" in imap_host else None,
                    "subject": subject,
                    "from_header": decode_mime_header(msg.get("From", "")),
                    "to_header": ", ".join(parse_addresses(msg.get("To", ""))),
                    "cc_header": ", ".join(parse_addresses(msg.get("Cc", ""))),
                    "text_body": text_body,
                    "html_body": html_body,
                    "has_attachment": bool(attachments_info),
                    "attachments": attachments_info,
                    "parsed_date": parsed_date,
                }
            except Exception as e:
                logger.error(f"[{address}] UID {uid_str} fetch 또는 파싱 중 오류 발생: {e}", exc_info=True)
                continue  # 개별 이메일 오류는 무시

        # 5. 스팸 필터 일괄 호출
        classification_results = {}
        if emails_for_llm:
            logger.info(f"[{address}] {len(emails_for_llm)}개 메일에 대한 스팸 분류를 시작합니다.")
            job = account.job or ""
            usage = account.usage or ""
            interests = account.interests or []
            try:
                classification_results = classify_emails_in_batch(
                    emails=emails_for_llm, job=job, usage=usage, interests=interests
                )
                logger.info(f"[{address}] 스팸 분류 완료. 결과 수: {len(classification_results)}")
            except Exception as e:
                logger.error(f"[{address}] 스팸 필터 일괄 호출 중 오류 발생: {e}", exc_info=True)
                # 스팸 필터 실패해도 동기화는 계속 진행
        else:
            logger.info(f"[{address}] 스팸 분류할 메일이 없습니다.")

        # 6. DB에 저장 (2차 루프)
        logger.info(f"[{address}] {len(processed_email_data)}개 메일에 대한 DB 저장을 시작합니다.")
        all_success = True  # 모든 메일이 성공적으로 저장되었는지 추적하는 플래그
        for uid_str, data in processed_email_data.items():
            try:
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
                    synced_count += 1
                    logger.info(f"[{address}] UID {uid_str} DB 저장 완료.")
            except Exception as e:
                logger.error(f"[{address}] UID {uid_str} DB 저장 중 오류 발생: {e}", exc_info=True)
                all_success = False  # 실패 시 플래그를 False로 변경

        # 마지막 동기화 시간 업데이트 (핵심 변경 부분)
        if all_success and uids_to_fetch:
            account.last_synced = timezone.now()
            account.save(update_fields=["last_synced"])
            logger.info(
                f"[{address}] 모든 메일이 성공적으로 저장되어 마지막 동기화 시간을 {account.last_synced}로 업데이트했습니다."
            )
        elif not uids_to_fetch:
            # 가져올 메일이 원래 없었던 경우에도 동기화 시간은 업데이트
            account.last_synced = timezone.now()
            account.save(update_fields=["last_synced"])
            logger.info(f"[{address}] 새 메일이 없어 마지막 동기화 시간만 업데이트합니다.")
        else:
            logger.warning(
                f"[{address}] 일부 메일 저장에 실패하여 마지막 동기화 시간을 업데이트하지 않습니다. 다음 동기화 시 재시도됩니다."
            )

        logger.info(f"[{address}] 동기화 작업 완료. 총 {synced_count}개의 새 메일을 저장했습니다.")
        return synced_count

    except Exception as e:
        # 이 블록은 IMAP 조회/처리 로직의 예기치 않은 오류를 잡기 위함
        logger.critical(f"[{address}] 동기화 프로세스 중 예기치 않은 심각한 오류 발생: {e}", exc_info=True)
        raise e  # View가 오류를 인지하도록 다시 발생시킴
    finally:
        if imap:
            try:
                imap.close()
                imap.logout()
                logger.info(f"[{address}] IMAP 연결을 정상적으로 닫고 로그아웃했습니다.")
            except Exception as e:
                logger.warning(f"[{address}] IMAP 연결 종료 중 오류 발생: {e}", exc_info=True)
