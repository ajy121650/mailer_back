# mailer_back

## 프론트엔드 개발자를 위한 빠른 테스트 가이드

이 가이드는 백엔드 프로젝트를 처음 실행하는 프론트엔드 개발자를 위해 작성되었습니다. 아래 단계만 따라 하면 바로 테스트 가능한 서버를 실행할 수 있습니다.

### 사전 준비
-   Python 3.10 이상 버전이 설치되어 있어야 합니다.

---

### 1단계: 프로젝트 클론

```bash
git clone <repository_url>
cd mailer_back
```

### 2단계: Python 가상 환경 생성 및 활성화

프로젝트의 의존성을 시스템과 격리하기 위해 가상 환경을 사용합니다.

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```
이제 터미널 프롬프트 앞에 `(.venv)`가 표시됩니다.

### 3단계: 의존성 패키지 설치

`pip`를 사용하여 필요한 모든 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

### 4단계: `.env` 파일 설정

API 키 등 민감한 정보를 설정합니다. `.env.example` 파일을 복사하여 `.env` 파일을 만드세요.

```bash
cp .env.example .env
```

그 다음, 생성된 `.env` 파일을 열어 아래 항목들을 채워주세요.

1.  **`FERNET_KEY`**: 이메일 비밀번호 암호화 키입니다. 아래 명령어로 생성하여 붙여넣으세요.
    ```bash
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```

2.  **`SECRET_KEY`**: Django 보안 키입니다. 아래 명령어로 생성하여 붙여넣으세요.
    ```bash
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    ```

3.  **`EMAIL_ADDRESS` / `EMAIL_PASSWORD`**: 이메일 동기화 테스트를 위해 실제 사용하는 **Gmail 계정** 정보를 입력해주세요. (앱 비밀번호 사용 권장)
(앱 비밀번호 생성: https://myaccount.google.com/apppasswords?rapt=AEjHL4N99hr0cASdIjZb5gvzt9EriTkYp3s0oR_KCneUuvaG59FRY8obQKYdF3arhu1JS9Zqt2OzElEeOkey5C5NIsinpWfSPi-Djyv-70uRd0etuoOMAY4)

4.  **`GOOGLE_API_KEY`**: 스팸 필터링 기능을 위해 필요합니다. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 빠르게 발급받을 수 있습니다. (없어도 서버 실행은 가능)

5.  **`CLERK_TURN_OFF` / `S3_TURN_OFF`**: **반드시 `True`로 설정해주세요.** Clerk 인증 및 S3 파일 업로드를 비활성화하여 로컬 환경에서 쉽게 API를 테스트할 수 있습니다.
    ```env
    CLERK_TURN_OFF=True
    S3_TURN_OFF=True
    ```

완성된 `.env` 파일은 아래와 같은 모습입니다.
```env
#이메일 암호화용 FERNET 키
FERNET_KEY=91v24r'80kp'1v24r80k-

#장고 내에서 사용하는 SECRET_KEY
SECRET_KEY=1k9184tv1v24rk980-

#스팸 필터 호출용 LLM_API_KEY
GOOGLE_API_KEY="API 키"

#이메일 불러오기 위한 계정정보
EMAIL_ADDRESS="test@test.com"
EMAIL_PASSWORD="xxxx xxxx xxxx xxxx" (16자)

# Clerk 인증 비활성화
CLERK_TURN_OFF=True

# S3 업로드 비활성화
S3_TURN_OFF=True
```

### 5단계: 데이터베이스 및 테스트 데이터 생성

아래 두 명령어를 순서대로 실행하여 데이터베이스를 만들고, API 테스트에 필요한 기본 사용자(`testuser`)와 이메일 계정을 생성합니다.

```bash
python manage.py migrate
python test_setup.py
```

### 6단계: 개발 서버 실행

모든 준비가 끝났습니다! 아래 명령어로 서버를 실행하세요.

```bash
python manage.py runserver
```

### 7단계: API 테스트

-   서버가 `http://127.0.0.1:8000/` 에서 실행됩니다.
-   모든 API 엔드포인트 문서는 **`http://127.0.0.1:8000/api/swagger/`** 에서 확인할 수 있습니다.
-   `CLERK_TURN_OFF=True`이므로, 모든 API 요청은 자동으로 `testuser`로 인증됩니다. 별도의 인증 헤더 없이 바로 API를 테스트할 수 있습니다.
