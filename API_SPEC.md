# Mailer API 명세서

## 1. 사용자 인증 (User Authentication)

### 1.1. 인증 흐름 개요

본 프로젝트의 인증은 Clerk 서비스를 통해 처리됩니다. 전체적인 흐름은 다음과 같습니다.

- **Clerk**: 사용자 정보 관리, 회원가입/로그인 UI 제공, 인증 성공 시 JWT(JSON Web Token) 발급을 담당합니다.
- **프론트엔드**: Clerk이 제공하는 UI를 사용자에게 보여주고, 로그인 성공 후 발급된 JWT를 저장합니다. 이후 백엔드 API를 호출할 때마다 이 JWT를 `Authorization` 헤더에 담아 보냅니다.
- **백엔드**: API 요청이 들어올 때마다 프론트엔드가 보낸 JWT의 유효성을 검증하여 사용자를 식별합니다. 토큰 자체를 서버에 저장하지 않는 **상태 비저장(Stateless)** 방식으로 동작합니다.

### 1.2. 회원가입 (Sign-up)

- **주체**: 프론트엔드 + Clerk
- **흐름**:
  1. 사용자가 프론트엔드에서 '회원가입'을 시작합니다.
  2. 프론트엔드는 Clerk이 제공하는 회원가입 UI를 사용자에게 보여줍니다.
  3. 사용자는 Clerk UI를 통해 정보를 입력하고 가입을 완료합니다. **이 과정은 백엔드 서버와 전혀 통신하지 않습니다.**
  4. 가입 성공 시, Clerk은 새로운 **Clerk User ID**를 생성합니다.

- **백엔드에서의 후속 처리 (최초 API 요청 시)**:
  1. 가입한 사용자가 처음으로 백엔드 API를 호출하면, `ClerkAuthentication` 미들웨어가 동작합니다.
  2. 헤더에 담긴 JWT에서 Clerk User ID를 추출한 뒤, 이 ID가 우리 `User` DB에 있는지 확인합니다.
  3. **DB에 없다면, 해당 Clerk User ID를 `user_id` 필드에 저장하여 새로운 `User` 레코드를 자동으로 생성합니다.** (`get_or_create` 로직)
  4. 이 시점부터 Clerk 사용자와 백엔드 `User` 데이터가 1:1로 매핑됩니다.

### 1.3. 로그인 (Login)

- **주체**: 프론트엔드 + Clerk
- **흐름**:
  1. 사용자가 프론트엔드에서 '로그인'을 시작합니다.
  2. 프론트엔드는 Clerk의 로그인 UI를 사용자에게 보여줍니다.
  3. 로그인 성공 시, Clerk은 JWT를 생성하여 프론트엔드에 전달합니다.
  4. 프론트엔드는 이 JWT를 안전하게 저장하고, 이후 모든 백엔드 API 요청의 `Authorization` 헤더에 담아 전송합니다.
- **백엔드 역할**: 로그인 과정 자체에는 관여하지 않으며, 각 API 요청의 JWT를 검증하여 사용자를 식별할 뿐입니다.

### 1.4. 로그아웃 (Logout)

- **주체**: 프론트엔드
- **흐름**:
  1. 사용자가 '로그아웃'을 요청합니다.
  2. 프론트엔드는 Clerk SDK를 호출하여 Clerk 세션을 종료시킵니다.
  3. **가장 중요한 단계로, 프론트엔드는 자신이 저장하고 있던 JWT를 폐기(삭제)합니다.**
- **백엔드 역할**: 전혀 관여하지 않습니다. 로그아웃은 전적으로 클라이언트(프론트엔드)의 토큰 관리 정책에 따릅니다.

### 1.5. 회원 탈퇴 (Delete Account)

- **주체**: 프론트엔드 + 백엔드 + Clerk
- **흐름**:
  1. 사용자가 프론트엔드에서 '회원 탈퇴'를 요청합니다.
  2. 프론트엔드는 백엔드의 회원 탈퇴 API를 호출합니다.

- **API 명세**:
  - **Method**: `DELETE`
  - **Endpoint**: `/api/user/delete/`
  - **설명**: 요청을 보낸 사용자의 백엔드 DB 정보를 모두 삭제하고, 성공 시 프론트엔드가 Clerk 계정까지 삭제하도록 유도합니다.

- **백엔드 역할**:
  1. API 요청 헤더의 JWT를 통해 사용자를 식별합니다.
  2. DB에서 해당 `User` 레코드와, 그에 종속된 모든 데이터(이메일 계정, 주소록, 템플릿 등)를 삭제합니다. (`on_delete=models.CASCADE`)
  3. 성공적으로 삭제되었음을 프론트엔드에 알립니다.

- **프론트엔드 후속 처리**:
  1. 백엔드로부터 성공 응답(`204 No Content`)을 받습니다.
  2. **(필수) Clerk SDK를 호출하여 Clerk에 등록된 실제 사용자 정보까지 삭제합니다.** (이 단계를 생략하면 우리 DB에서는 삭제됐지만 Clerk에는 계정이 남게 됩니다.)
  3. 로컬에 저장된 JWT를 삭제하고 사용자를 완전히 로그아웃시킵니다.

- **Success Response**:
  - **Code**: `204 No Content`
- **Error Response**:
  - **Code**: `401 Unauthorized`
    ```json
    { "detail": "Authentication credentials were not provided." }
    ```
  - **Code**: `500 Internal Server Error`
    ```json
    { "detail": "An unexpected error occurred on the server." }
    ```

---

## 2. 이메일 계정 관리 (Email Account Management)

### 2.1. 연동된 메일 계정 목록 조회
- **Method**: `GET`
- **Endpoint**: `/api/account/`
- **설명**: 현재 로그인된 사용자가 연동한 모든 이메일 계정 목록을 조회합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    [
      {
        "id": 1,
        "address": "user1@example.com",
        "domain": "example.com",
        "is_valid": true,
        "last_synced": "2025-10-28T10:00:00Z"
      }
    ]
    ```
- **Error Response**:
  - **Code**: `401 Unauthorized`

### 2.2. 메일 계정 연동
- **Method**: `POST`
- **Endpoint**: `/api/account/`
- **설명**: 새로운 이메일 계정을 연동합니다. 비밀번호는 암호화되어 저장됩니다.
- **Request Body**:
  ```json
  {
    "address": "new_user@gmail.com",
    "password": "very-secret-password",
    "domain": "imap.gmail.com"
  }
  ```
- **Success Response**:
  - **Code**: `201 Created`
    ```json
    {
      "id": 2,
      "address": "new_user@gmail.com",
      "domain": "imap.gmail.com",
      "is_valid": true,
      "last_synced": null
    }
    ```
- **Error Response**:
  - **Code**: `400 Bad Request` (요청 데이터 유효성 검사 실패 시)
    ```json
    { "address": ["Enter a valid email address."] }
    ```
  - **Code**: `409 Conflict` (이미 연동된 계정일 경우)
    ```json
    { "detail": "This email account is already registered." }
    ```

### 2.3. 연동된 메일 계정 삭제
- **Method**: `DELETE`
- **Endpoint**: `/api/account/{account_id}/`
- **설명**: 지정된 ID의 이메일 계정 연동을 삭제합니다.
- **Success Response**:
  - **Code**: `204 No Content`
- **Error Response**:
  - **Code**: `403 Forbidden` (자신의 계정이 아닐 경우)
    ```json
    { "detail": "You do not have permission to perform this action." }
    ```
  - **Code**: `404 Not Found`
    ```json
    { "detail": "Not found." }
    ```

---

## 3. 주소록 (Contacts / Favorites)

### 3.1. 즐겨찾기 목록 조회
- **Method**: `GET`
- **Endpoint**: `/api/contact/{account_id}/`
- **설명**: 특정 이메일 계정에 등록된 즐겨찾기 주소 목록을 조회합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    [
      { "id": 1, "address": "friend@example.com" },
      { "id": 2, "address": "boss@work.com" }
    ]
    ```
- **Error Response**:
  - **Code**: `403 Forbidden`
  - **Code**: `404 Not Found`

### 3.2. 즐겨찾기 추가
- **Method**: `POST`
- **Endpoint**: `/api/contact/{account_id}/`
- **설명**: 특정 이메일 계정에 새로운 주소를 즐겨찾기로 추가합니다.
- **Request Body**:
  ```json
  { "address": "new_friend@example.com" }
  ```
- **Success Response**:
  - **Code**: `201 Created`
    ```json
    { "id": 3, "address": "new_friend@example.com" }
    ```
- **Error Response**:
  - **Code**: `400 Bad Request`
  - **Code**: `409 Conflict`

### 3.3. 즐겨찾기 삭제
- **Method**: `DELETE`
- **Endpoint**: `/api/contact/{account_id}/{contact_id}/`
- **설명**: 특정 이메일 계정의 즐겨찾기에서 주소를 삭제합니다.
- **Success Response**:
  - **Code**: `204 No Content`
- **Error Response**:
  - **Code**: `403 Forbidden`
  - **Code**: `404 Not Found`

---

## 4. AI 기능 (AI Features)

### 4.1. 메일 요약 요청
- **Method**: `POST`
- **Endpoint**: `/api/email/{email_metadata_id}/summarize/`
- **설명**: 특정 메일의 요약을 LLM에 요청하고 결과를 받아 저장합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    {
      "id": 123,
      "summarized_content": "이것은 LLM이 요약한 내용입니다...",
      "is_summarized": true
    }
    ```
- **Error Response**:
  - **Code**: `404 Not Found`
  - **Code**: `503 Service Unavailable` (LLM 서비스 문제 발생 시)
    ```json
    { "detail": "The summarization service is currently unavailable." }
    ```

---

## 5. 템플릿 (Templates)

### 5.1. 전체 공개 템플릿 목록 조회
- **Method**: `GET`
- **Endpoint**: `/api/template/`
- **설명**: 모든 사용자가 볼 수 있는 공개 템플릿 목록을 조회합니다.
- **Query Parameters**: `main_category`, `sub_category`
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    [
      {
        "id": 101,
        "main_category": "인사",
        "sub_category": "안부",
        "template_title": "오랜만이야",
        "template_content": "잘 지내? 오랜만이야."
      }
    ]
    ```

### 5.2. 공개 템플릿 상세 조회
- **Method**: `GET`
- **Endpoint**: `/api/template/{template_id}/`
- **설명**: 특정 공개 템플릿의 상세 내용을 조회합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    {
      "id": 101,
      "main_category": "인사",
      "sub_category": "안부",
      "template_title": "오랜만이야",
      "template_content": "잘 지내? 오랜만이야."
    }
    ```
- **Error Response**:
  - **Code**: `404 Not Found`

### 5.3. 계정별 템플릿 목록 조회
- **Method**: `GET`
- **Endpoint**: `/api/account/{account_id}/templates/`
- **설명**: 특정 이메일 계정에 저장된 템플릿 목록을 조회합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    [
      {
        "id": 1,
        "main_category": "업무",
        "sub_category": "보고",
        "template_title": "주간 업무 보고",
        "template_content": "주간 업무 보고 드립니다."
      }
    ]
    ```
- **Error Response**:
  - **Code**: `403 Forbidden`
  - **Code**: `404 Not Found`

### 5.4. 계정별 템플릿 생성
- **Method**: `POST`
- **Endpoint**: `/api/account/{account_id}/templates/`
- **설명**: 특정 이메일 계정에 템플릿을 새로 생성합니다.
- **Request Body**:
  ```json
  {
    "main_category": "업무",
    "sub_category": "보고",
    "template_title": "주간 업무 보고",
    "template_content": "주간 업무 보고 드립니다."
  }
  ```
- **Success Response**:
  - **Code**: `201 Created`
- **Error Response**:
  - **Code**: `400 Bad Request`

### 5.5. 계정별 템플릿 수정
- **Method**: `PATCH`
- **Endpoint**: `/api/account/{account_id}/templates/{template_id}/`
- **설명**: 특정 이메일 계정의 템플릿을 수정합니다.
- **Request Body**:
  ```json
  {
    "template_title": "월간 업무 보고",
    "template_content": "월간 업무 보고 드립니다."
  }
  ```
- **Success Response**:
  - **Code**: `200 OK`
- **Error Response**:
  - **Code**: `400 Bad Request`
  - **Code**: `403 Forbidden`
  - **Code**: `404 Not Found`

### 5.6. 계정별 템플릿 삭제
- **Method**: `DELETE`
- **Endpoint**: `/api/account/{account_id}/templates/{template_id}/`
- **설명**: 특정 이메일 계정의 템플릿을 삭제합니다.
- **Success Response**:
  - **Code**: `204 No Content`
- **Error Response**:
  - **Code**: `403 Forbidden`
  - **Code**: `404 Not Found`

---

## 6. 메일 관리 (Email Management)

### 6.1. 메일 목록 조회 및 검색
- **Method**: `GET`
- **Endpoint**: `/api/metadata/`
- **설명**: 사용자의 모든 연동 계정에 대한 메일 목록을 조회합니다. 여러 조건으로 필터링 및 검색이 가능합니다.
- **Query Parameters**:
  - `accounts` (optional, string): 콤마(`,`)로 구분된 이메일 주소 목록. 특정 계정의 메일만 필터링합니다. (예: `user1@example.com,user2@work.com`)
  - `folder` (optional, string): `inbox`, `sent`, `starred`, `spam`, `trash` 중 하나를 지정하여 특정 폴더의 메일만 필터링합니다.
  - `query` (optional, string): 검색어. 메일의 제목, 본문, 발신자, 수신자 필드에서 해당 검색어를 포함하는 메일을 필터링합니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    [
      {
        "id": 1,
        "account_address": "user1@example.com",
        "folder": "inbox",
        "is_read": false,
        "is_important": true,
        "is_pinned": false,
        "received_at": "2025-10-28T14:31:00Z",
        "email": {
          "subject": "회의록 전달",
          "from_header": "colleague@example.com",
          "date": "2025-10-28T14:30:00Z",
          "preview": "안녕하세요, 지난 회의록 전달 드립니다..."
        }
      }
    ]
    ```
- **Error Response**:
  - **Code**: `401 Unauthorized`
  - **Code**: `400 Bad Request` (존재하지 않거나 권한 없는 `accounts` 파라미터 요청 시)
    ```json
    { "detail": "You do not have permission for the following accounts: ['wrong@email.com']" }
    ```

### 6.2. 메일 상세 조회
- **Method**: `GET`
- **Endpoint**: `/api/metadata/{email_metadata_id}/`
- **설명**: 특정 메일의 상세 정보를 조회합니다. 이 API를 호출하면 해당 메일은 자동으로 '읽음'(`is_read: true`) 상태로 변경됩니다.
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    {
      "id": 1,
      "account_address": "user1@example.com",
      "folder": "inbox",
      "is_read": true,
      "is_important": true,
      "is_pinned": false,
      "received_at": "2025-10-28T14:31:00Z",
      "email": {
        "subject": "회의록 전달",
        "from_header": "colleague@example.com",
        "to_header": ["user1@example.com"],
        "cc_header": [],
        "bcc_header": [],
        "text_body": "안녕하세요, 지난 회의록 전달 드립니다...",
        "html_body": "<p>안녕하세요, 지난 회의록 전달 드립니다...</p>",
        "date": "2025-10-28T14:30:00Z"
      }
    }
    ```
- **Error Response**:
  - **Code**: `401 Unauthorized`
  - **Code**: `404 Not Found`

### 6.3. 메일 상태 변경
- **Method**: `PATCH`
- **Endpoint**: `/api/metadata/{email_metadata_id}/`
- **설명**: 특정 메일의 상태를 변경합니다. 폴더 이동, 읽음/안읽음 처리, 중요 표시 등을 할 수 있습니다.
- **Request Body**:
  ```json
  {
    "folder": "trash",
    "is_read": true,
    "is_important": false,
    "is_pinned": true
  }
  ```
- **Success Response**:
  - **Code**: `200 OK`
    ```json
    {
      "id": 1,
      "account_address": "user1@example.com",
      "folder": "trash",
      "is_read": true,
      "is_important": false,
      "is_pinned": true,
      "received_at": "2025-10-28T14:31:00Z",
      "email": {
        "subject": "회의록 전달",
        "from_header": "colleague@example.com",
        "to_header": ["user1@example.com"],
        "cc_header": [],
        "bcc_header": [],
        "text_body": "안녕하세요, 지난 회의록 전달 드립니다...",
        "html_body": "<p>안녕하세요, 지난 회의록 전달 드립니다...</p>",
        "date": "2025-10-28T14:30:00Z"
      }
    }
    ```
- **Error Response**:
  - **Code**: `400 Bad Request`
  - **Code**: `401 Unauthorized`
  - **Code**: `404 Not Found`

### 6.4. 메일 삭제
- **Method**: `DELETE`
- **Endpoint**: `/api/metadata/{email_metadata_id}/`
- **설명**: 메일을 삭제합니다. 동작 방식은 메일의 현재 위치에 따라 달라집니다.
  - **일반 폴더에 있는 경우**: 메일을 휴지통(`trash`)으로 이동시킵니다.
  - **휴지통에 있는 경우**: 메일을 영구적으로 삭제(Soft Delete)합니다.
- **Success Response**:
  - **Code**: `200 OK` (휴지통으로 이동 성공 시, 이동된 메일 정보를 반환)
    ```json
    {
      "id": 1,
      "account_address": "user1@example.com",
      "folder": "trash",
      "is_read": true,
      "is_important": false,
      "is_pinned": false,
      "received_at": "2025-10-28T14:31:00Z",
      "email": {
        "subject": "회의록 전달",
        "from_header": "colleague@example.com",
        "to_header": ["user1@example.com"],
        "cc_header": [],
        "bcc_header": [],
        "text_body": "안녕하세요, 지난 회의록 전달 드립니다...",
        "html_body": "<p>안녕하세요, 지난 회의록 전달 드립니다...</p>",
        "date": "2025-10-28T14:30:00Z"
      }
    }
    ```
  - **Code**: `204 No Content` (영구 삭제 성공 시)
- **Error Response**:
  - **Code**: `401 Unauthorized`
  - **Code**: `404 Not Found`

### 6.5. 메일 발송 (Send Email)
- **Method**: `POST`
- **Endpoint**: `/api/account/{account_id}/send/`
- **설명**: 지정된 계정을 사용하여 새로운 메일을 발송합니다. `EmailContent` 모델의 필드를 기반으로 메일 내용을 구성합니다.
- **Request Body**:
  ```json
  {
    "to": ["recipient1@example.com"],
    "cc": ["recipient2@example.com"],
    "bcc": ["recipient3@example.com"],
    "subject": "API 명세서 초안",
    "text_body": "안녕하세요, API 명세서 초안 전달드립니다.",
    "html_body": "<p>안녕하세요, API 명세서 초안 전달드립니다.</p>",
    "attachment_ids": [1, 5]
  }
  ```
- **Success Response**:
  - **Code**: `202 Accepted`
    ```json
    {
      "status": "accepted",
      "message": "Email has been queued for sending."
    }
    ```
- **Error Response**:
  - **Code**: `400 Bad Request` (수신자, 제목, 내용 등 필수 필드 누락 또는 형식 오류)
  - **Code**: `401 Unauthorized`
  - **Code**: `403 Forbidden` (해당 계정으로 메일을 보낼 권한이 없는 경우)
  - **Code**: `404 Not Found` (존재하지 않는 `account_id`인 경우)
  - **Code**: `503 Service Unavailable` (외부 SMTP 서버 등 발송 서비스에 문제가 있는 경우)