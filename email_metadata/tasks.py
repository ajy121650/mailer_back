"""Celery Tasks for email_metadata 앱.

기능 추가:
1. 스팸 미분류 메타데이터 주기적 분류(classify_unprocessed_metadata)
2. 큐 상태 로깅(log_spam_queue_depth)

개선 사항:
- 로깅 추가
- 재시도(retry) 로직 추가 (네트워크 등 일시 오류 가정)
- 레이트 리밋(rate_limit) 설정
- 안전한 저장 (이미 다른 워커가 처리한 경우 skip)
"""

import logging
import time
from celery import shared_task
from django.db import transaction
from email_metadata.models import EmailMetadata
from utils.spam_filter import classify_emails_in_batch

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    rate_limit="80/m",  # 분당 80건 그룹 처리 (LLM 호출 수 제어용)
)
def classify_unprocessed_metadata(self, batch_size=30, sleep=1.0):
    """is_spammed가 NULL인 EmailMetadata를 계정별로 묶어 LLM 분류.

    batch_size: 최대 선택 row 수
    sleep: 그룹 처리 후 잠깐 쉬는 시간 (백투백 호출 완화)
    """
    # 1차 조회 (경합을 줄이기 위해 작은 배치)
    candidates = list(
        EmailMetadata.objects.select_related("email", "account")
        .filter(is_spammed__isnull=True)
        .order_by("id")[:batch_size]
    )
    if not candidates:
        logger.debug("분류 대상 없음")
        return 0

    # 계정별 그룹화
    groups: dict[int, list[EmailMetadata]] = {}
    for meta in candidates:
        groups.setdefault(meta.account_id, []).append(meta)

    updated = 0
    for metas in groups.values():
        account = metas[0].account
        job = getattr(account, "job", "") or ""
        usage = getattr(account, "usage", "") or ""
        interests = getattr(account, "interests", []) or []

        payload = []
        mapping: dict[str, EmailMetadata] = {}
        for meta in metas:
            body = meta.email.text_body or meta.email.html_body or ""
            sid = str(meta.id)
            payload.append({"id": sid, "subject": meta.email.subject or "", "body": body})
            mapping[sid] = meta

        if not payload:
            continue

        try:
            result = classify_emails_in_batch(payload, job=job, interests=interests, usage=usage)
        except Exception as e:  # 광범위 예외 (LLM / 네트워크 오류)
            logger.warning("LLM 분류 실패: account_id=%s metas=%s error=%s", account.id, [m.id for m in metas], e)
            # 재시도 가능한 상황이라고 가정 (최대 max_retries)
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                logger.error("최대 재시도 초과: account_id=%s", account.id)
                continue

        # 원자적 저장: 이미 다른 워커가 값을 채운 경우 skip
        with transaction.atomic():
            # 최신 상태 재조회 + 행 잠금 (선택적) -> SQLite는 select_for_update 미지원, 따라서 단순 재검사
            ids = [m.id for m in metas]
            fresh_map = {m.id: m for m in EmailMetadata.objects.select_related("email").filter(id__in=ids)}
            for sid, label in result.items():
                meta = mapping.get(sid)
                if not meta:
                    continue
                fresh = fresh_map.get(meta.id)
                if not fresh or fresh.is_spammed is not None:
                    # 이미 처리됨 (다른 워커 선행) or 존재 안함
                    continue
                spam = label == "spam"
                fresh.is_spammed = spam
                fresh.folder = "spam" if spam else "inbox"
                fresh.save(update_fields=["is_spammed", "folder", "synced_at"])
                updated += 1

        time.sleep(sleep)  # LLM 호출 사이 완화

    logger.info("스팸 분류 처리 완료: updated=%s", updated)
    return updated


@shared_task(bind=True, rate_limit="20/m")
def log_spam_queue_depth(self):  # noqa: D401 (단순 로그용)
    """남은 스팸 분류 대기 row 수를 로그로 남김."""
    remaining = EmailMetadata.objects.filter(is_spammed__isnull=True).count()
    logger.info("스팸 분류 대기 개수: %s", remaining)
    return remaining
