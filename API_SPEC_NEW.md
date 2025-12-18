# 📄 Mailer API 명세서 (v2 - 최종)

## 1. 사용자 인증 및 관리

### 1.1. 인증 흐름 개요

본 프로젝트의 인증은 **Clerk** 서비스를 통해 처리된다.

- **Clerk**: 사용자 정보 관리, 회원가입/로그인 UI 제공, JWT 발급
- **프론트엔드**: Clerk UI 연동, 발급된 JWT 저장 및 API 요청 시 헤더에 전송
- **백엔드**: JWT 유효성 검증 (Stateless 방식)

### 1.2. 회원가입 및 로그인

Clerk가 제공하는 UI와 SDK를 통해 처리되므로 백엔드에 별도의 회원가입/로그인 API는 없습니다. 사용자가 최초로 API를 호출할 때, 백엔드는 JWT의 Clerk User ID를 확인하여 DB에 `User` 레코드를 자동 생성합니다.

### 1.3. 내 정보 조회

```
GET /api/user/me/
```

- **설명**: 현재 로그인된 사용자의 간단한 정보(DB `id`와 `user_id`)를 조회합니다.
- **Success Response**: `200 OK`
    ```json
    {
      "user_id": "user_xxxxxxxxxxxx",
      "id": 1
    }
    ```
- **Error Response**: `401 Unauthorized`

### 1.4. 강제 로그아웃

```
POST /api/user/signout/
```

- **설명**: 현재 사용자의 Clerk 세션을 서버에서 강제로 만료시킵니다. 일반적인 로그아웃은 프론트에서 JWT를 삭제하여 처리하지만, 보안상 필요할 때 이 API를 사용할 수 있습니다.
- **Success Response**: `200 OK`
    ```json
    { "ok": true }
    ```
- **Error Response**:
    - `400 Bad Request`: 토큰에 세션 ID가 없는 경우.
    - `500 Internal Server Error`: Clerk API 통신 실패 시.

### 1.5. 서버 헬스 체크

```
GET /api/user/health/
```

- **설명**: 서버가 정상적으로 동작하는지 확인하는 공개 엔드포인트입니다.
- **Success Response**: `200 OK`
    ```json
    { "ok": true }
    ```

---

## 2. 이메일 계정 관리 (email_account)

### 2.1. 연동된 메일 계정 목록 조회

```
GET /api/account/
```

- **설명**: 현재 로그인된 사용자가 연동한 모든 이메일 계정 목록을 조회합니다.
- **Success Response**: `200 OK`
    ```json
    [
      {
        "id": 1,
        "address": "user1@example.com",
        "domain": "example",
        "is_valid": true,
        "last_synced": "2025-10-28T10:00:00Z",
        "job": "데이터 분석가",
        "usage": "학교용",
        "interests": ["금융", "부동산"]
      }
    ]
    ```
- **Error Response**: `401 Unauthorized`

### 2.2. 메일 계정 연동

```
POST /api/account/
```

- **설명**: 새로운 이메일 계정을 연동합니다. 백엔드에서 IMAP 서버 접속을 테스트하여 유효성을 검증하며, 비밀번호는 암호화되어 저장됩니다.
- **Request Body**:
    ```json
    {
      "address": "new_user@gmail.com",
      "password": "gmail-app-password"
    }
    ```
- **Success Response**: `201 Created`
    ```json
    {
      "id": 2,
      "address": "new_user@gmail.com",
      "domain": "gmail",
      "is_valid": true,
      "last_synced": null,
      "job": null,
      "usage": null,
      "interests": []
    }
    ```
- **Error Response**:
    - `400 Bad Request`: 이메일/비밀번호 오류 또는 지원하지 않는 도메인일 경우.
    - `409 Conflict`: 이미 등록된 계정일 경우.

### 2.3. 연동된 메일 계정 삭제

```
DELETE /api/account/{account_id}/
```

- **설명**: 지정된 ID의 이메일 계정 연동을 삭제합니다.
- **Success Response**: `204 No Content`
- **Error Response**: `404 Not Found` (해당 계정을 찾을 수 없거나 권한이 없을 경우)

### 2.4. 메일 계정 프로필 설정/수정

```
PATCH /api/account/{account_id}/profile/
```

- **설명**: 지정된 이메일 계정(`account_id`)의 프로필(직업, 용도, 관심사)을 설정하거나 수정합니다.
- **Request Body**: (모든 필드는 선택적)
    ```json
    {
      "job": "데이터 분석가",
      "usage": "학교용",
      "interests": ["금융", "부동산"]
    }
    ```
- **Success Response**: `200 OK` (수정 후 프로필 정보)
- **Error Response**:
    - `400 Bad Request`: 유효성 검사 실패 시.
    - `404 Not Found`: 해당 계정을 찾을 수 없거나 권한이 없을 경우.

### 2.5. 메일 수동 동기화

```
POST /api/account/{account_id}/sync/
```

- **설명**: 특정 이메일 계정의 메일을 수동으로 동기화합니다. 새로 동기화된 메일의 개수를 반환합니다.
- **Success Response**: `200 OK`
    ```json
    {
        "message": "user@example.com의 동기화가 완료되었습니다.",
        "synced_count": 15
    }
    ```
- **Error Response**:
    - `404 Not Found`: 계정을 찾을 수 없거나 권한이 없을 경우.
    - `500 Internal Server Error`: IMAP 동기화 실패 시.

---

## 3. 메일 관리

### 3.1. 메일 목록 조회 및 검색

```
GET /api/email/
```

- **설명**: 사용자의 모든 연동 계정에 대한 메일 목록을 조회합니다. 여러 조건으로 필터링 및 검색이 가능합니다.
- **Query Parameters**:
    - `accounts` (optional, string): 콤마(`,`)로 구분된 이메일 주소 목록.
    - `folder` (optional, string): `inbox`, `sent`, `starred`, `spam`, `trash` 중 하나.
    - `query` (optional, string): 검색어 (제목, 본문, 발신자, 수신자 대상).
- **Success Response**: `200 OK`
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
          "to_header": ["user1@example.com"],
          "date": "2025-10-28T14:30:00Z",
          "preview": "안녕하세요, 지난 회의록 전달 드립니다..."
        }
      }
    ]
    ```
- **Error Response**:
    - `400 Bad Request`: 권한 없는 `accounts` 파라미터 요청 시.
    - `401 Unauthorized`: 로그인하지 않았을 시.

### 3.2. 개별 이메일 조회, 수정, 삭제

```
GET, PATCH, DELETE /api/email/{email_id}/
```

- **설명**: 특정 ID(`email_id`)를 가진 이메일 하나에 대한 조회, 수정, 삭제 작업을 수행합니다.

#### GET (상세 조회)
- **설명**: 메일의 상세 정보를 조회합니다. 이 API를 호출하면 해당 메일은 자동으로 **'읽음'(`is_read: true`) 상태로 변경**됩니다.
- **Success Response**: `200 OK`
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
        "date": "2025-10-28T14:30:00Z",
        "attachments": [
          {
            "id": 1,
            "file_name": "report.pdf",
            "file_size": 102400,
            "mime_type": "application/pdf"
          }
        ]
      }
    }
    ```

#### PATCH (상태 변경)
- **설명**: 메일의 상태(폴더, 읽음 여부, 중요 표시 등)를 변경합니다.
- **Request Body**: (변경할 필드만 전송)
    ```json
    {
      "folder": "trash",
      "is_read": true,
      "is_important": false,
      "is_pinned": true
    }
    ```
- **Success Response**: `200 OK` (변경 완료된 전체 메일 상세 정보 반환)

#### DELETE (삭제)
- **설명**: 메일을 삭제합니다.
    - **일반 폴더**: 메일을 휴지통(`trash`)으로 이동시킵니다. (응답: `200 OK`와 함께 이동된 메일 정보)
    - **휴지통**: 메일을 영구적으로 삭제(Soft Delete)합니다. (응답: `204 No Content`)

- **Error Response (for all methods)**: `404 Not Found`

### 3.3. 메일 발송

```
POST /api/email/send/
```

- **설명**: 지정된 계정을 사용하여 새로운 메일을 발송하고, 보낸편지함에 저장합니다.
- **Request Body**:
    ```json
    {
      "account_id": 1,
      "to": ["recipient1@example.com"],
      "cc": ["recipient2@example.com"],
      "bcc": ["recipient3@example.com"],
      "subject": "API 명세서 초안",
      "body": "<p>안녕하세요, API 명세서 초안 전달드립니다.</p>",
      "is_html": true
    }
    ```
- **Success Response**: `200 OK`
    ```json
    {
      "message": "이메일이 성공적으로 전송되었습니다."
    }
    ```
- **Error Response**:
    - `400 Bad Request`: 필수 필드 누락 또는 형식 오류.
    - `401 Unauthorized`: SMTP 인증 실패 시.
    - `404 Not Found`: 존재하지 않는 `account_id`인 경우.

---

## 4. 첨부파일 (Attachment)

### 4.1. 첨부파일 다운로드

```
GET /api/attachments/{attachment_id}/download/
```

- **설명**: 특정 ID(`attachment_id`)의 첨부파일을 다운로드합니다. 사용자는 자신이 소유한 이메일에 속한 첨부파일만 다운로드할 수 있습니다.
- **Success Response**: `200 OK` (File Stream)
- **Error Response**: `404 Not Found`

---

## 5. 주소록 (Contact)

### 5.1. 즐겨찾기 목록 조회 및 추가

```
GET, POST /api/contact/{account_id}/
```
- **설명**: 특정 이메일 계정(`account_id`)에 대한 즐겨찾기 주소를 조회하거나 추가합니다.

#### GET (목록 조회)
- **Success Response**: `200 OK`
    ```json
    [
      { "id": 1, "address": "friend@example.com" }
    ]
    ```

#### POST (추가)
- **Request Body**: `{ "address": "new_friend@example.com" }`
- **Success Response**: `201 Created`
- **Error Response**: `409 Conflict` (이미 주소가 존재할 경우)

### 5.2. 즐겨찾기 수정 및 삭제

```
PATCH, DELETE /api/contact/{contact_id}/
```
- **설명**: 특정 연락처(`contact_id`)를 수정하거나 삭제합니다.

#### PATCH (수정)
- **Request Body**: `{ "address": "re_friend@example.com" }`
- **Success Response**: `200 OK`

#### DELETE (삭제)
- **Success Response**: `204 No Content`

- **Error Response (for all methods)**: `404 Not Found`

---

## 6. 메일 요약

### 6.1. 메일 요약 요청

```
POST /api/email/{email_id}/summarize/
```
- **설명**: 특정 메일의 요약을 요청합니다. 이미 요약된 내용이 있으면 즉시 반환하고, 없으면 LLM을 통해 생성 후 저장 및 반환합니다.
- **Success Response**: `200 OK`
    ```json
    {
      "id": 123,
      "summarized_content": "이것은 LLM이 요약한 내용입니다...",
      "is_summarized": true
    }
    ```

### 6.2. 메일 요약 재생성 요청

```
POST /api/email/{email_id}/resummarize/
```
- **설명**: 기존 요약 내용과 상관없이 강제로 요약을 다시 생성합니다.
- **Success Response**: `200 OK`

---

## 7. 템플릿 (Template)

- **공개 템플릿**: 관리자가 제공하는 모든 사용자가 조회 가능한 기본 템플릿.
- **내 템플릿**: 사용자가 직접 생성하거나 공개 템플릿을 복사하여 특정 계정에 귀속시킨 템플릿.

### 공개 템플릿 (View Template)

#### 7.1. 전체 공개 템플릿 목록 조회

```
GET /api/template/viewtemplate/
```
- **설명**: 관리자가 생성한 모든 공개 템플릿 목록을 조회합니다.

#### 7.2. 공개 템플릿 상세 조회 및 저장

```
GET, POST /api/template/viewtemplate/{template_id}/
```

- **GET (상세 조회)**: 특정 공개 템플릿(`template_id`)의 상세 내용을 조회합니다.
- **POST (내 템플릿으로 저장)**: 특정 공개 템플릿을 내 여러 이메일 계정으로 복사하여 '내 템플릿'으로 저장합니다.
    - **Request Body**: `{ "email_account_ids": [1, 2] }`
    - **Success Response**: `201 Created` (생성된 '내 템플릿' 객체 목록 반환)

### 내 템플릿 (My Template)

#### 7.3. 내 템플릿 전체 목록 조회

```
GET /api/template/mytemplate/list/{user_pk}/
```
- **설명**: 특정 사용자(`user_pk`)가 소유한 모든 템플릿을 조회합니다.

#### 7.4. 내 템플릿 신규 생성

```
POST /api/template/mytemplate/create/
```
- **설명**: 하나 이상의 이메일 계정에 대한 새 개인 템플릿을 생성합니다.
- **Request Body**:
    ```json
    {
      "email_account_ids": [1, 2],
      "template_title": "새로운 템플릿 제목",
      "template_content": "템플릿 내용입니다.",
      "sub_category": "업무",
      "topic": "주간 보고"
    }
    ```
- **Success Response**: `201 Created`

#### 7.5. 내 템플릿 상세 조회, 수정, 삭제

```
GET, PUT, DELETE /api/template/mytemplate/{template_id}/
```
- **설명**: 내가 소유한 특정 템플릿(`template_id`)을 조회, 수정, 삭제합니다.
- **GET**: 상세 정보를 조회합니다.
- **PUT**: 내용을 수정합니다. (`PATCH`가 아닌 `PUT` 사용)
    - **Request Body**: (수정할 전체 필드)
        ```json
        {
          "sub_category": "수정된 서브 카테고리",
          "topic": "수정된 토픽",
          "template_title": "수정된 제목",
          "template_content": "수정된 내용입니다."
        }
        ```
- **DELETE**: 템플릿을 삭제합니다. (`204 No Content`)
