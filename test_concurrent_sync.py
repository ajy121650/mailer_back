"""
동시 이메일 동기화 요청 테스트

여러 사용자가 동시에 이메일 동기화를 요청할 때
응답 시간과 동작을 테스트합니다.
"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 설정
BASE_URL = "http://localhost:8000"
API_ENDPOINT = "/api/account"

# 테스트 계정 ID 리스트 (실제 계정 ID로 변경)
ACCOUNT_IDS = [4, 1]

# Clerk 토큰 (테스트용, 실제 토큰으로 변경)
# TestAuthentication을 사용 중이면 임의의 토큰 가능
AUTH_TOKEN = "test_token"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
}


def sync_email_account(account_id: int) -> dict:
    """
    단일 이메일 계정 동기화 요청

    Args:
        account_id: 동기화할 계정 ID

    Returns:
        응답 데이터 딕셔너리
    """
    url = f"{BASE_URL}{API_ENDPOINT}/{account_id}/sync/"

    start_time = time.time()

    try:
        response = requests.post(url, headers=HEADERS, timeout=600)  # 10분 타임아웃
        elapsed_time = time.time() - start_time

        return {
            "account_id": account_id,
            "status_code": response.status_code,
            "elapsed_time": elapsed_time,
            "response": response.json(),
            "success": response.status_code == 200,
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "account_id": account_id,
            "status_code": None,
            "elapsed_time": elapsed_time,
            "response": str(e),
            "success": False,
        }


def test_sequential_requests():
    """순차 요청 테스트 (비교용)"""
    print("\n" + "=" * 60)
    print("순차 요청 테스트 (Sequential)")
    print("=" * 60)

    total_start = time.time()

    results = []
    for account_id in ACCOUNT_IDS:
        print(f"\n[순차] 계정 {account_id} 동기화 시작...")
        result = sync_email_account(account_id)
        results.append(result)
        print(f"[순차] 계정 {account_id}: {result['elapsed_time']:.2f}초 소요 (상태: {result['status_code']})")

    total_time = time.time() - total_start

    print(f"\n순차 요청 총 시간: {total_time:.2f}초")
    return results, total_time


def test_concurrent_requests(max_workers: int = 3):
    """동시 요청 테스트"""
    print("\n" + "=" * 60)
    print(f"동시 요청 테스트 (Concurrent, max_workers={max_workers})")
    print("=" * 60)

    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 요청을 큐에 등록
        futures = {executor.submit(sync_email_account, account_id): account_id for account_id in ACCOUNT_IDS}

        # 완료된 요청부터 결과 처리
        for future in as_completed(futures):
            account_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"[동시] 계정 {account_id}: {result['elapsed_time']:.2f}초 소요 (상태: {result['status_code']})")
            except Exception as e:
                print(f"[동시] 계정 {account_id} 에러: {e}")

    total_time = time.time() - total_start

    print(f"\n동시 요청 총 시간: {total_time:.2f}초")
    return results, total_time


def print_summary(seq_results, seq_time, con_results, con_time):
    """테스트 결과 요약"""
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    print("\n[순차 요청]")
    for result in seq_results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} 계정 {result['account_id']}: {result['elapsed_time']:.2f}초")
    print(f"  총 시간: {seq_time:.2f}초")

    print("\n[동시 요청]")
    for result in con_results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} 계정 {result['account_id']}: {result['elapsed_time']:.2f}초")
    print(f"  총 시간: {con_time:.2f}초")

    # 성능 개선 계산
    if seq_time > 0:
        improvement = ((seq_time - con_time) / seq_time) * 100
        speedup = seq_time / con_time
        print("\n성능 개선:")
        print(f"  속도 향상: {speedup:.2f}배")
        print(f"  시간 단축: {improvement:.1f}%")
        print(f"  예상 소요 시간: {seq_time:.2f}초 → {con_time:.2f}초")


def test_with_logging():
    """로깅과 함께 상세 테스트"""
    print("\n" + "=" * 60)
    print("상세 로깅 테스트 (Real-time timing)")
    print("=" * 60)

    def log_sync(account_id):
        print(f"\n[{time.strftime('%H:%M:%S')}] 계정 {account_id} 동기화 시작")
        result = sync_email_account(account_id)
        print(f"[{time.strftime('%H:%M:%S')}] 계정 {account_id} 동기화 완료 ({result['elapsed_time']:.2f}초)")
        return result

    start = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(log_sync, aid) for aid in ACCOUNT_IDS]
        results = [f.result() for f in as_completed(futures)]

    total = time.time() - start
    print(f"\n[{time.strftime('%H:%M:%S')}] 모든 동기화 완료 (총 {total:.2f}초)")
    return results, total


if __name__ == "__main__":
    print("\n🚀 동시 요청 테스트 시작\n")

    # 서버 연결 확인
    try:
        response = requests.get(f"{BASE_URL}/api/account/", headers=HEADERS, timeout=5)
        print(f"✅ 서버 연결 확인 (상태: {response.status_code})")
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("   django runserver를 실행하세요: python manage.py runserver")
        exit(1)

    # 테스트 실행
    print(f"\n📊 테스트 계정 ID: {ACCOUNT_IDS}")
    print("⏱️  각 동기화 대략 30초 예상\n")

    # 1. 순차 요청
    seq_results, seq_time = test_sequential_requests()
    time.sleep(2)  # 사이에 딜레이

    # 2. 동시 요청
    con_results, con_time = test_concurrent_requests(max_workers=3)

    # 3. 결과 요약
    print_summary(seq_results, seq_time, con_results, con_time)

    # 4. 상세 로깅 (선택)
    print("\n\n🔍 상세 타이밍 로그")
    log_results, log_time = test_with_logging()

    print("\n✅ 테스트 완료!")
