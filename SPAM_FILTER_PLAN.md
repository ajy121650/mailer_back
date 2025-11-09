# 최종_하이브리드_스팸_필터링_시스템_구축_계획.md

## 1. 최종 목표
LLM(거대 언어 모델)을 **초기 규칙 생성기(Initial Rule Generator)**로 활용하고, **사용자 피드백을 통해 스스로 학습(Self-Tuning)**하는 지능형 스팸 처리 시스템을 구축한다.

---

## 2. 핵심 아키텍처: 개별 요소 가중치 조정(Individual Factor Weight Adjustment)
LLM은 필터링 규칙의 '초안'만 생성한다. 시스템의 핵심은, 사용자의 피드백을 바탕으로 규칙을 구성하는 **개별 요소(키워드, 발신자 패턴 등)의 가중치를 동적으로 조정**하여 스스로를 정밀하게 튜닝하는 로컬 엔진이다.

```
[관심사 변경 시] -> [LLM 규칙 생성기 호출] -> [초기 규칙(JSON) 저장]
       ^                                            |
       | (규칙 성능 저하 시)                          v
[새 이메일 수신] -> [1. 기본 필터] -> [2. 학습된 규칙(로컬) 필터] -> [분류 완료]
       ^                                                              |
       |                                                              v
       +---[3. 피드백 루프: 개별 가중치 조정 및 규칙 재학습 트리거]----+                                                              
```

---

## 3. 개발 단계 (Phases)

### Phase 1: 데이터 모델 수정 [완료]
- **목표**: 사용자 관심사 및 LLM이 생성/학습한 필터링 규칙을 저장할 필드를 추가한다.
- **수정 파일**: `email_account/models.py`
- **수정 내용**: `EmailAccount` 모델에 `interests`와 `filter_rules` 필드 추가.
  ```python
  class EmailAccount(models.Model):
      # ... 기존 필드 ...
      interests = models.JSONField(
          null=True, blank=True, default=dict, 
          help_text="사용자 관심사 (예: {'likes': ['AI', 'Python'], 'dislikes': ['부동산']})"
      )
      filter_rules = models.JSONField(
          null=True, blank=True, default=dict,
          help_text="LLM이 생성하고 피드백으로 학습된 개인화 필터링 규칙 (JSON)"
      )
      # ... 기존 필드 ...
  ```
- **후속 조치**:
  1. `python manage.py makemigrations email_account`
  2. `python manage.py migrate`

### Phase 2: LLM 규칙 생성기 구현 [완료]
- **목표**: `interests`를 바탕으로 `filter_rules`의 초안을 생성하는 서비스를 구현한다.
- **생성 파일**: `email_account/services.py`
- **구현 내용**:
  1. `generate_initial_rules(account)` 함수:
     - `account.interests`를 기반으로 LLM에 보낼 프롬프트 생성.
     - **프롬프트 예시**: "...스팸 필터링 규칙을 JSON으로 만들어주세요. 각 규칙 요소에는 고유 id, 타입, 내용, 초기 가중치(weight)를 포함해주세요."
     - LLM API를 호출하여 `account.filter_rules`에 저장.
  2. 이 로직을 트리거할 API 엔드포인트 생성 (예: `POST /api/account/<account_id>/generate-rules/`).

### Phase 3: 로컬 필터 엔진 구현 [완료]
- **목표**: 저장된 `filter_rules`를 해석하여 이메일의 최종 점수를 계산하는 엔진을 구현한다.
- **생성 파일**: `email_content/filters.py`
- **구현 내용**:
  1. `calculate_score(email_content, rules)` 함수:
     - `rules`의 각 `factor`들을 `email_content`와 대조.
     - 매칭되는 모든 `factor`의 `weight`를 합산하여 최종 점수를 반환.

### Phase 4: 피드백 기반 가중치 조정 엔진 구현 [완료]
- **목표**: 사용자 피드백(오분류 수정)이 발생했을 때, 원인이 된 `factor`의 `weight`를 자동으로 조정한다.
- **생성 파일**: `email_content/tuning.py`
- **구현 내용**:
  1. `tune_weights_on_feedback(account, email_content, correct_classification)` 함수:
     - `email_content`에 포함된 `factor`들을 식별.
     - `correct_classification`이 'spam'인데 'inbox'로 분류된 경우(False Negative), 식별된 `factor`들의 `weight`를 낮춤.
     - `correct_classification`이 'inbox'인데 'spam'으로 분류된 경우(False Positive), 식별된 `factor`들의 `weight`를 높임.
     - 변경된 `rules`를 `account.filter_rules`에 다시 저장.
  2. `MarkAsSpamAPIView` / `MarkAsNotSpamAPIView` 내에서 위 함수를 호출.

### Phase 5: 전체 프로세스 통합 및 자동 재학습
- **목표**: 모든 컴포넌트를 통합하고, 시스템 성능 저하 시 자동으로 규칙을 재 생성하는 로직을 추가한다.
- **수정/생성 파일**: `email_content/services.py`
- **구현 내용**:
  1. `classify_email(email_content, account)` 메인 함수:
     - **1단계 (기본 필터)**: `SpamedMail` 차단 목록 확인.
     - **2단계 (로컬 규칙 필터)**: `calculate_score` 호출 및 `base_threshold`와 비교하여 분류.
     - `EmailMetadata.folder` 업데이트.
  2. **자동 규칙 재학습 트리거**:
     - `tune_weights_on_feedback` 함수 실행 횟수가 단기간에 급증하는 것을 감지하는 로직 추가.
     - 성능 저하가 감지되면, 백그라운드에서 `generate_initial_rules`를 호출하여 규칙을 초기화하고 다시 학습을 시작.

---

## 4. 다음 단계
모든 핵심 로직 구현이 완료되었습니다. 다음 단계는 **Phase 5: 전체 프로세스 통합**으로, 구현된 함수들을 실제 Django API와 연동하는 작업입니다.

---

## 5. 논의 기록(2025-09-28 23:17 기준) (Discussion Log)

- **아키텍처 진화 과정**:
  1. 초기 아이디어: 이메일마다 LLM을 호출하여 스팸을 분류.
  2. 비용 문제 제기: 모든 이메일에 LLM을 호출하는 것은 비용 부담이 큼.
  3. 개선안 1: LLM을 '실시간 분류기'가 아닌 '규칙 생성기'로 사용하기로 결정. LLM은 사용자 관심사에 따라 로컬에서 실행될 JSON 규칙을 생성.
  4. 애매한 케이스 처리 논의: 규칙 점수가 애매한 경우를 위해 '검토 필요' 폴더를 제안했으나, 사용자 경험(UX)을 해친다는 우려로 기각.
  5. 최종 아키텍처 확정: '자동 조정 임계값' 아이디어를 발전시켜, 사용자 피드백에 따라 단일 임계값이 아닌 **개별 규칙(Factor)의 가중치(Weight)를 직접 조정**하는 현재의 'Self-Tuning' 방식으로 최종 결정.

- **기술 및 구조 결정 사항**:
  - **LLM 라이브러리**: `google-genai` 사용 확정. `genai.Client()`를 생성하는 객체 지향 방식으로 구현.
  - **파일 구조**: 스팸 필터링 로직은 특정 앱에 종속되지 않도록, 프로젝트 루트에 `utils/` 디렉터리를 생성하고 `spam_filter.py` 파일 내에서 중앙 관리하기로 결정.
  - **필터링 순서**: '기본 필터(차단 목록)'를 먼저 확인하여, 통과된 이메일만 '규칙 기반 필터'로 점수를 계산하는 2단계 방식을 채택. 이는 불필요한 계산을 줄이는 '빠른 경로 최적화'로 판단.