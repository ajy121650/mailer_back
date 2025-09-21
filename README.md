# mailer_back

## 백엔드를 위한 가이드

### 1. uv 설치

uv 설치법
curl -LsSf https://astral.sh/uv/install.sh | sh # uv 설치
<br>
source $HOME/.cargo/env #환경변수 설정

가상환경 생성 및 활성화
uv venv
source .venv/bin/activate

uv sync

이후 패키지 추가 필요 시
uv add 패키지명

---

### 2. 프로젝트 환경 설정 (Initial Setup)

이 프로젝트를 실행하려면 보안을 위한 환경 변수 설정이 필요합니다. 프로젝트 루트에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 만드세요.

```bash
cp .env.example .env
```

그런 다음, 아래의 명령어를 사용하여 `SECRET_KEY`와 `FERNET_KEY`를 생성하고, 생성된 키를 `.env` 파일에 각각 붙여넣으세요.

#### 1. SECRET_KEY 생성

Django에서 사용하는 비밀 키입니다. 아래 명령어를 실행하여 키를 생성하세요.

```bash
.venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### 2. FERNET_KEY 생성

이메일 계정의 비밀번호를 암호화하는 데 사용되는 키입니다. 아래 명령어를 실행하여 키를 생성하세요.

```bash
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

#### .env 파일 예시

위에서 생성된 키들을 `.env` 파일에 아래와 같은 형식으로 저장해야 합니다.

```
SECRET_KEY=your_generated_secret_key_here
FERNET_KEY=your_generated_fernet_key_here
```

---

### 3. pre-commit 설정 활성화

아래의 코드를 실행하면 pre-commit 설정이 활성화 됩니다. 저희는 린터/포매터로 ruff와 black을 사용중입니다.

```bash
pre-commit install
```

## 🚀 프론트엔드를 위한 가이드

이 문서는 Mailer 프로젝트의 백엔드 설정을 위한 가이드입니다.

### 1단계: `uv` 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2단계: 가상 환경 생성 및 활성화

프로젝트 루트 디렉토리에서 아래 명령어를 실행하여 가상 환경을 만들고 활성화합니다.

```bash
uv venv
source .venv/bin/activate
```

### 3단계: 의존성 패키지 설치

`uv.lock` 파일에 명시된 모든 의존성 패키지를 설치합니다.

```bash
uv sync
```

### 4단계: 환경 변수 설정(로컬 테스트용)

보안 키들을 담고 있는 `.env` 파일을 설정합니다.

1.  먼저, `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.

2.  아래 명령어를 실행하여 `SECRET_KEY`와 `FERNET_KEY`를 각각 생성합니다.

    - **SECRET_KEY 생성:**
      ```bash
      .venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
      ```
    - **FERNET_KEY 생성:**
      ```bash
      .venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
      ```

3.  생성된 두 개의 키를 복사하여 `.env` 파일 안에 각각 붙여넣습니다.
    ```
    SECRET_KEY=your_generated_secret_key_here
    FERNET_KEY=your_generated_fernet_key_here
    ```

### 6단계: 데이터베이스 설정

아래 명령어를 실행하여 데이터베이스 테이블을 생성하고 초기화합니다.

```bash
.venv/bin/python manage.py migrate
```

### 6-1 : 더미데이터 세팅

```bash
python manage.py seed_test_data
```

테스트용 계정:
username='testuser',
defaults={'password': 'testpassword123'}
생성 및 3개의 test email 연결.
각 email당 20개의 테스트 메일, 총 60개 메일을 랜덤한 folder에 저장.

### 7단계: 개발 서버 실행

모든 설정이 완료되었으면, 아래 명령어를 사용하여 개발 서버를 실행합니다.

```bash
.venv/bin/python manage.py runserver
```

서버가 정상적으로 실행되면, 웹 브라우저에서 `http://127.0.0.1:8000/api/swagger` 주소로 접속할 수 있습니다.
