# API 명세서

---

# 📄 Mailer API 명세서

## 1. 사용자 인증

#로 감싼 내용은 딱히 백엔드에서 별도의 절차가 필요하지는 않은 듯.

##################################################################

### 1.1. 인증 흐름 개요

본 프로젝트의 인증은 **Clerk** 서비스를 통해 처리된다.

- **Clerk**: 사용자 정보 관리, 회원가입/로그인 UI 제공, JWT 발급
- **프론트엔드**: Clerk UI 연동, 발급된 JWT 저장 및 API 요청 시 헤더에 전송
- **백엔드**: JWT 유효성 검증 (Stateless 방식)

### 1.2. 회원가입

- **주체**: 프론트엔드 + Clerk
- **흐름**:
    1. 사용자가 프론트엔드에서 회원가입을 시작한다.
    2. 프론트엔드는 Clerk 회원가입 UI를 렌더링한다.
    3. 사용자는 Clerk UI를 통해 가입을 완료한다.
    4. 가입 성공 시, Clerk은 새로운 **Clerk User ID**를 생성한다.

> [Backend] 백엔드 후속 처리 (최초 API 요청 시)
> 
> 1. 가입한 사용자가 처음 API를 호출하면 `ClerkAuthentication` 미들웨어가 JWT에서 Clerk User ID를 추출한다.
> 2. 해당 ID가 `User` DB에 있는지 확인한다.
> 3. **DB에 없다면, Clerk User ID를 `user_id` 필드에 저장하여 새 `User` 레코드를 자동 생성한다.** (`get_or_create` 로직)
> 4. 이 시점부터 Clerk 사용자와 백엔드 `User`가 1:1 로 매핑된다.

### 1.3. 로그인 (Login)

- **주체**: 프론트엔드 + Clerk
- **흐름**:
    1. 사용자가 프론트엔드에서 로그인을 시작한다.
    2. 프론트엔드는 Clerk 로그인 UI를 렌더링한다.
    3. 로그인 성공 시, Clerk은 JWT를 생성하여 프론트엔드에 전달한다.
    4. 프론트엔드는 JWT를 안전하게 저장하고, 이후 모든 API 요청의 `Authorization` 헤더에 담아 전송한다.
- **백엔드 역할**: 로그인 과정 자체에는 관여하지 않으며, API 요청 시 JWT를 검증할 뿐이다. 즉, 로그인을 위한 별도의 API가 필요하지는 않다.

### 1.4. 로그아웃 (Logout)

- **주체**: 프론트엔드
- **흐름**:
    1. 사용자가 로그아웃을 요청한다.
    2. 프론트엔드는 Clerk SDK를 호출하여 Clerk 세션을 종료시킨다.
    3. 프론트엔드는 로컬에 저장하고 있던 JWT를 폐기한다.
- **백엔드 역할: 따로 관여하지 않음. 굳이 하고자 한다면 user_id 삭제? → 이러면 아예 계정 삭제라 굳이 할 필요 없을듯**

#######################################################################

사실상 API는 여기부터.

### 1.5. 회원 탈퇴 (Delete Account)

```jsx
DELETE /api/user/delete/
```

- **설명**: 요청을 보낸 사용자의 백엔드 DB 정보(User, 연동 계정, 주소록 등)를 모두 삭제한다.
- **백엔드 역할**:
    1. JWT를 통해 사용자를 식별한다.
    2. DB에서 해당 `User` 레코드와 모든 종속 데이터(Email 계정, 주소록, 템플릿 등)를 삭제한다. (`on_delete=models.CASCADE`)
    3. 성공 응답(204)을 반환한다.
- **Success Response**:
    - **Code**: `204 No Content`
- **Error Response**:
    - **Code**: `401 Unauthorized`JSON
    
    ```jsx
    { "detail": "Authentication credentials were not provided." }
    ```
    
    - **Code**: `500 Internal Server Error`JSON
    
    ```jsx
    { "detail": "An unexpected error occurred on the server." }
    ```
    

> [Frontend] 프론트엔드 후속 처리
> 
> 1. 백엔드로부터 `204 No Content` 응답을 받는다.
> 2. **(필수) Clerk SDK를 호출하여 Clerk에 등록된 실제 사용자 정보까지 삭제한다.** (이 단계를 생략하면 우리 DB에서는 삭제됐지만 Clerk에는 계정이 남게 됨.)
> 3. 로컬에 저장된 JWT를 삭제하고 사용자를 완전히 로그아웃시킨다.

---

## 2. 이메일 계정 관리 (email_account)

```jsx
GET /api/account/
```

### 2.1. 연동된 메일 계정 목록 조회

- **설명**: 현재 로그인된 사용자가 연동한 모든 이메일 계정 목록을 조회한다. 이렇게 조회한 계정들은 이하의 api들에서 사용될 수 있다.
- **Success Response**:
    - **Code**: `200 OK`JSON
        
        ```jsx
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
    - **Code**: `401 Unauthorized` (mailer 로그인 안한 상태일 시.)

### 2.2. 메일 계정 연동

```jsx
POST /api/account/
```

- **설명**: 새로운 이메일 계정을 연동한다. 비밀번호는 암호화되어 저장된다.
- **Request Body**:
    
    ```jsx
    {
      "address": "new_user@gmail.com",
      "password": "very-secret-password",
      "domain": "imap.gmail.com"
    }
    ```
    
- **Success Response**:
    - **Code**: `201 Created`
        
        ```jsx
        {
          "id": 2,
          "address": "new_user@gmail.com",
          "domain": "imap.gmail.com",
          "is_valid": true,
          "last_synced": null
        }
        ```
        
- **Error Response**:
    - **Code**: `400 Bad Request`
        
        ```jsx
        { "address": ["Enter a valid email address."] }
        ```
        
    - **Code**: `409 Conflict`
        
        ```jsx
        { "detail": "This email account is already registered." }
        ```
        

### 2.3. 연동된 메일 계정 삭제

```jsx
DELETE /api/account/{account_id}/
```

- **설명**: 지정된 ID의 이메일 계정 연동을 삭제한다.
- **Success Response**:
    - **Code**: `204 No Content`
- **Error Response**:
    - **Code**: `403 Forbidden` (자신의 계정이 아닐 경우)
        
        ```jsx
        { "detail": "You do not have permission to perform this action." }
        ```
        
    - **Code**: `404 Not Found` (해당 계정을 찾을 수 없을 경우)
        
        ```jsx
        { "detail": "Not found." }
        ```
        

### 2.4. 메일 계정 프로필 설정&수정 → ~~우리 메일 계정에 이런것도 저장해..?~~

A. figma에 요거 반영하는 용도

![image.png](attachment:5a495ac6-f6ff-4c0b-94b9-20a30085e1e2:image.png)

```jsx
PATCH /api/account/{account_id}/profile/
```

- **설명**: 지정된 이메일 계정(`account_id`)의 프로필을 설정하거나 수정한다. `PATCH` 메서드이므로, **변경하려는 필드만** 요청 바디에 담아 보낼 수 있다. 해당 프로필은 이후 스팸 필터링에 사용된다.
- **Request Body**: (모든 필드는 선택적)
    
    ```jsx
    {
    	"job": "데이터 분석가"
      "usage": "학교용"
    	"interests": ["금융", "부동산"], (리스트 형태)
      
    }
    ```
    
    - 위 필드 중 일부만 담아서 업데이트할 수도 있다.
- **Success Response**:
    - **Code**: `200 OK` (수정 후 응답)
        
        ```jsx
        {
        	"job": "데이터 분석가"
          "usage": "학교용"
        	"interests": ["금융", "부동산"], (리스트 형태)
        }
        ```
        
- **Error Response**:
    - **Code**: `400 Bad Request` (요청 데이터 유효성 검사 실패 시, 예: `interests`가 리스트가 아닐 경우)
        
        ```jsx
        { "interests": ["This field must be a list."] }
        ```
        
    - **Code**: `401 Unauthorized` (mailer 앱에 로그인하지 않은 경우)
    - **Code**: `403 Forbidden` (내 메일계정이 아닌 경우)
    - **Code**: `404 Not Found` (해당 메일 계정이 연결되지 않은 경우)

---

## 3. 메일 관리

### 3.1. 메일 목록 조회 및 검색

```jsx
GET /api/email/
```

- **설명**: 사용자의 모든 연동 계정에 대한 메일 목록을 조회한다. 여러 조건으로 필터링 및 검색이 가능하다.
- **Query Parameters**:
    - `accounts` (optional, string): 콤마(`,`)로 구분된 이메일 주소 목록. 특정 계정의 메일만 필터링한다. (예: `user1@example.com,user2@work.com`)
    - `folder` (optional, string): `inbox`, `sent`, `starred`, `spam`, `trash` 중 하나를 지정하여 특정 폴더의 메일만 필터링한다.
    - `query` (optional, string): 검색어. 메일의 제목, 본문, 발신자, 수신자 필드에서 해당 검색어를 포함하는 메일을 필터링한다.
- **Success Response**:
    - **Code**: `200 OK`
        
        ```jsx
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
    - **Code**: `401 Unauthorized` (로그인하지 않았을 시)
    - **Code**: `400 Bad Request` (존재하지 않거나 권한 없는 `accounts` 파라미터 요청 시)
        
        ```jsx
        {
          "detail": "You do not have permission for the following accounts: ['wrong@email.com']"
        }
        ```
        

---

### 3.2. 메일 상세 조회 ← 여기에 Attachment 불러오기위한 필드 추가해야함

```jsx
GET /api/email/{email_metadata_id}/
```

- **설명**: 특정 메일의 상세 정보를 조회한다.
- **특징**: 이 API를 호출하면 해당 메일은 백엔드에서 자동으로 **'읽음'(`is_read: true`) 상태로 변경된다**.
- **Success Response**:
    - **Code**: `200 OK`
        
        ```jsx
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
    - **Code**: `401 Unauthorized` (로그인 안했을 시)
    - **Code**: `404 Not Found` (해당 이메일이 없을 시)

---

### 3.3. 메일 상태 변경

```jsx
PATCH /api/metadata/{email_metadata_id}/
```

- **설명**: 특정 메일의 상태를 변경한다. 폴더 이동, 읽음/안읽음 처리, 중요 표시 등을 할 수 있다.
- **Request Body**: (변경할 필드만 전송하면 됨)
    
    ```
      {
        "folder": "trash", <-- 제한 없음. (inbox -> trash, trash -> inbox도 가능)
        "is_read": true,
        "is_important": false,
        "is_pinned": true
      }
    ```
    
- **Success Response**:
    - **Code**: `200 OK` (변경 완료된 전체 메일 상세 정보 반환)
    
    ```
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
    - **Code**: `400 Bad Request` (잘못된 request body 사용시)
    - **Code**: `401 Unauthorized` (로그인 안했을 시)
    - **Code**: `404 Not Found` (해당 메일이 없을 시)

---

### 3.4. 메일 삭제

```jsx
DELETE /api/metadata/{email_metadata_id}/
```

- **설명**: 메일을 삭제합니다. 동작 방식은 메일의 현재 `folder` 상태에 따라 달라집니다.
    - **일반 폴더 (inbox 등)에 있는 경우**: 메일을 휴지통(`trash`)으로 이동시킵니다. (상태 변경. 사실상 patch와 동일한 동작이나 DELETE의 개념적 통일성을 위해 추가한 로직.)
    - **휴지통 (`trash`)에 있는 경우**: 메일을 영구적으로 삭제합니다. (Soft Delete 처리)
- **Success Response**:
    - **Code**: `200 OK` (휴지통으로 **이동** 성공 시, 즉, 현재 folder가 ‘trash’가 아닌 상황에서 삭제 성공시. 이동된 메일 정보를 반환)
    
    ```
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
    
    - **Code**: `204 No Content` (영구 **삭제** 성공 시. 즉, 휴지통에서 한 번 더 삭제할 시.)
- **Error Response**:
    - **Code**: `401 Unauthorized` (로그인 안했을 시)
    - **Code**: `404 Not Found` (해당 메일이 없을 시)

### 3.5. 메일 발송 (Send Email)

```jsx
POST /api/account/{account_id}/send/
```

- **설명**: 지정된 계정(`account_id`)을 사용하여 새로운 메일을 발송하고, 보낸 편지함에 내용을 저장합니다.
- **Request Body**: ← 이거 형식은 메일발송에 어느 field들이 필요한지 몰라서 일단 임시로 넣음.

```
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
    - **Code**: `202 Accepted` (메일 발송 접수 완료.)
    
    ```
        {
          "status": "accepted",
          "message": "Email has been queued for sending."
        }
    ```
    
- **Error Response**:
    - **Code**: `400 Bad Request` (수신자, 제목, 내용 등 필수 필드 누락 또는 형식 오류)
    - **Code**: `401 Unauthorized` (로그인 안했을 시)
    - **Code**: `403 Forbidden` (해당 계정으로 메일을 보낼 권한이 없는 경우)
    - **Code**: `404 Not Found` (존재하지 않는 `account_id`인 경우)
    - **Code**: `503 Service Unavailable` (외부 SMTP 서버 등 발송 서비스에 문제가 있는 경우)

---

## 4. 주소록 (Contact)

### 4.1. 즐겨찾기 목록 조회

```jsx
GET /api/contact/{account_id}/
```

- **설명**: 특정 이메일 계정(`account_id`)에 등록된 즐겨찾기 주소 목록을 조회한다.
- **Success Response**:
    - **Code**: `200 OK`
        
        ```jsx
        [
          { "id": 1, "address": "friend@example.com" },
          { "id": 2, "address": "boss@work.com" }
        ]
        ```
        
- **Error Response**:
    - **Code**: `400 Bad Request` (요청 형식이 잘못된 경우)
    - **Code**: `403 Forbidden` (내 메일계정이 아닌 경우)
    - **Code**: `404 Not Found` (헤당 메일 계정이 연결되지 않은 경우)

### 4.2. 즐겨찾기 추가

```jsx
POST /api/contact/{account_id}/
```

- **설명**: 특정 이메일 계정(`account_id`)에 새로운 주소를 즐겨찾기로 추가한다.
- **Request Body**:
    
    ```jsx
    { "address": "new_friend@example.com" }
    ```
    
- **Success Response**:
    - **Code**: `201 Created`
        
        ```jsx
        { "id": 3, "address": "new_friend@example.com" }
        ```
        
- **Error Response**:
    - **Code**: `400 Bad Request` (요청 형식이 잘못된 경우)
    - **Code**: `403 Forbidden` (내 메일계정이 아닌 경우)
    - **Code**: `409 Conflict` (이미 즐겨찾기에 추가되어 있는 경우)

### 4.3. 즐겨찾기 수정(시간 남으면 ㄱㄱ)

```jsx
PATCH /api/contact/{contact_id}/
```

- **설명**: 특정 연락처를 수정한다.
- **Request Body**:
    
    ```jsx
    { "address": "re_friend@example.com" }
    ```
    
- **Success Response**:
    - **Code**: `200 OK`
        
        ```jsx
        { "id": 3, "address": "re_friend@example.com" }
        ```
        
- **Error Response**:
    - **Code**: `400 Bad Request` (요청 형식이 잘못된 경우)
    - **Code**: `403 Forbidden` (내 메일계정이 아닌 경우)

### 4.4. 즐겨찾기 삭제

```jsx
DELETE /api/contact/{contact_id}/
```

- **설명**: 특정 이메일 계정(`account_id`)의 즐겨찾기에서 특정 주소(`contact_id`)를 삭제한다.
- **Success Response**:
    - **Code**: `204 No Content`
- **Error Response**:
    - **Code**: `400 Bad Request` (요청 형식이 잘못된 경우)
    - **Code**: `403 Forbidden` (내 메일계정이 아닌 경우)
    - **Code**: `404 Not Found` (해당 주소가 즐겨찾기 목록에 없는 경우)

---

## 5. 메일 요약

### 5.1. 메일 요약 요청(기본기능)

```jsx
POST /api/email/{email_metadata_id}/summarize/
```

- **설명**: 특정 메일(`email_metadata_id`)의 요약을 LLM에 요청하고 결과를 받아 DB에 저장한 후, 프론트엔드로 리턴한다.
- **백엔드 로직**: `is_summarized` 필드를 확인하여, **`False`일 경우에만 LLM을 호출한다**. `True`라면 DB에 저장된 기존 요약본을 즉시 반환한다.
- **Success Response**: `200 OK`
    
    ```jsx
    {
      "id": 123,
      "summarized_content": "이것은 LLM이 요약한 내용입니다...",
      "is_summarized": true
    }
    ```
    
- **Error Response**:
    - `Code: 403 Forbidden` (내 메일계정이 아닌 경우)
    - `Code: 404 Not Found` (해당 메일을 찾을 수 없을 경우)
    - `Code: 503 Service Unavailable` (LLM 서비스 문제 발생 시)
    
    ```jsx
    { "detail": "The summarization service got error. try again." }
    ```
    

### 5.2. 메일 요약 재생성 요청(필요 시 추가) → 좋은듯

```jsx
POST /api/email/{email_metadata_id}/resummarize/
```

- **설명**: 특정 메일(`email_metadata_id`)의 요약을 LLM에 강제로 다시 요청한다.
- **백엔드 로직**: `is_summarized` 필드와 관계없이, **항상 LLM을 새로 호출**하여 기존 `summarized_content`를 덮어쓴다.
- **Success Response**: `200 OK`
    
    ```jsx
    {
      "id": 123,
      "summarized_content": "이것은 LLM이 *새로* 요약한 내용입니다...",
      "is_summarized": true
    }
    ```
    
- **Error Response**:
    - `Code: 403 Forbidden` (내 메일계정이 아닌 경우)
    - `Code: 404 Not Found` (해당 메일을 찾을 수 없을 경우)
    - `Code: 503 Service Unavailable` (LLM 서비스 문제 발생 시)
    
    ```jsx
    { "detail": "The summarization service got error. try again." }
    ```
    

---

# 6. 템플릿 (Template) (구현 완)

템플릿은 공개 템플릿(View Template)과 내 템플릿(My Template)으로 나뉜다.

- **공개 템플릿**: 모든 사용자가 조회할 수 있는 기본 프리셋. → 이거는 admin 계정 만들고 db에 미리 등록해놓은 다음에 모든 user한테 제공하면 될듯.
- **내 템플릿**: 사용자가 '공개 템플릿'을 저장하거나, 직접 생성하여 특정 이메일 계정(email_account)에 귀속시킨다.

## 공개 템플릿 (View Template)

### 6.1. 전체 공개 템플릿 목록 조회 (구현 완)

```jsx
GET /api/templates/viewtemplate/
```

- **설명**: 모든 사용자가 볼 수 있는 공개 템플릿 프리셋 목록을 조회한다.
- **Success Response**: `200 OK`
    
    ```jsx
    [
      {
        "id": 101,
        "main_category": "인사",
        "sub_category": "안부",
        "topic": "템플릿 이름",
        "template_title": "오랜만이야",
        "template_content": "잘 지내? 오랜만이야."
      }
      // ...
    ]
    ```
    

![image.png](attachment:88055b3d-8542-4ca1-b352-76e386f36bb6:image.png)

프론트에 질문: 여기서 About에 들어가는게 Topic인지 아니면 template_content인지? template 설명을 위한 topic 필드가 꼭 필요한지, 아니면 다른 필드로 대체가능할지에 대한 질문입니당

### 6.2. 공개 템플릿 상세 조회 (구현 완)

```jsx
GET /api/template/viewtemplate/{template_id}/
```

- **설명**: 특정 공개 템플릿(`template_id`)의 상세 내용을 조회한다.
- **Success Response**: `200 OK`
    
    ```jsx
    {
      "id": 101,
      "main_category": "인사",
      "sub_category": "안부",
      "topic": "템플릿 이름",
      "template_title": "오랜만이야",
      "template_content": "잘 지내? 오랜만이야."
    }
    ```
    
- **Error Response**: `404 Not Found` (해당 템플릿을 찾을 수 없음)

### 6.3. 공개 템플릿 저장 (내 템플릿으로 가져오기) (구현 완)

```jsx
POST /api/templates/viewtemplate/{template_id}/
```

- **설명**: 특정 공개 템플릿(`template_id`)을 **선택한 내 이메일 계정들**로 복사하여 '내 템플릿'으로 저장합니다. (다중 선택 저장 기능)
- **Request Body**:
    
    ```jsx
    {
    	"user_id": 1,
      "email_account_ids": [1, 2, ...] (list)
    }
    ```
    
    - `account_ids`: (필수) 템플릿을 저장할 email_account의 ID 목록 (리스트).
- **Success Response**: `201 Created`
    - 저장에 성공한 템플릿 객체 목록(각각 어느 계정에 저장되었는지 포함)을 반환한다. response가 복잡하지 않도록 템플릿을 구분할 수 있는 최소한의 정보(template_title, id)만 반환한다.
    
    ```jsx
    [
      {
        "id": 50, // 새로 생성된 '내 템플릿' ID
        "template_title": "오랜만이야",
        "topic": "템플릿 이름",
        "email_account": {
          "id": 1,
          "address": "user1@gmail.com"
        }
      },
      {
        "id": 51, // 새로 생성된 '내 템플릿' ID
        "topic": "템플릿 이름",
        "email_account": {
          "id": 2,
          "address": "user1@naver.com"
        }
      }
    ] 
    ```
    
- **Error Response**:
    - `400 Bad Request`: `account_ids` 필드가 없거나 비어있을 때.
    - `403 Forbidden`: `account_ids`에 포함된 계정이 내 소유가 아닐 때.
    - `404 Not Found`: `{template_id}`의 공개 템플릿을 찾을 수 없을 때.

---

## Part 2. 내 템플릿 (My Template)

### 6.4. 내 템플릿 전체 목록 조회→ 이 부분에서 공용 템플릿과 자체 템플릿을 구분하기 위해서는 user_id가 필요함 ← 사실 이건 내 템플릿으로 가져온 시점에서 구분할 필요가 있나 싶어서 안넣은 거긴 함 ← 애초에 db에서 찾기위해 이게(user_id) 필요함 (구현 완)

```jsx
GET /api/templates/mytemplate/list/{user_id}
```

- **설명**: **로그인한 사용자가 소유한 모든 이메일 계정의 템플릿**을 한꺼번에 조회한다.
- **Success Response**: `200 OK`
    - 각 템플릿이 어느 계정 소속인지 `account` 객체(id, address)를 포함하여 반환한다.
    
    ```jsx
    [
      {
        "id": 1,
        "main_category": "업무",
        "sub_category": "보고",
        "topic": "템플릿 이름",
        "template_title": "주간 업무 보고",
        "template_content": "주간 업무 보고 드립니다.",
        "email_account": {
          "id": 1,
          "address": "user1@gmail.com"
        }
      },
      {
        "id": 2,
        "main_category": "인사",
        "sub_category": "안부",
        "topic": "템플릿 이름",
        "template_title": "오랜만이야",
        "template_content": "잘 지내?",
        "email_account": {
          "id": 2,
          "address": "user2@naver.com"
        }
      },
      ...
    ]
    ```
    
- `401 Unauthorized`: mailer 로그인 안한 상태일 시.

### 6.4-1. 내 템플릿 상세 조회 (구현 완)

```jsx
GET /api/templates/mytemplate/{template_id}/
```

- **설명**: **사용자가 선택한 템플릿**을 조회한다.
- **Success Response**: `200 OK`

```jsx
[
  {
    "id": 1,
    "main_category": "업무",
    "sub_category": "보고",
    "topic": "템플릿 이름",
    "template_title": "주간 업무 보고",
    "template_content": "주간 업무 보고 드립니다.",
    "email_account": {
      "id": 1,
      "address": "user1@gmail.com"
    }
]
```

- `401 Unauthorized`: mailer 로그인 안한 상태일 시.
- `404 Not Found`:  해당 템플릿을 찾을 수 없을 때.

### 6.5. 내 템플릿 신규 생성 (구현 완)

```jsx
POST /api/templates/mytemplate/create/
```

- **설명**: 새로운 템플릿을 작성하여 특정 이메일 계정(`email_account_id`)에 저장한다. 이 때 main_category는 “개인 템플릿”으로 기입한다.
- **Query Parameters**:
    - `email_account_id` :  탬플릿을 저장하고자 하는 이메일 계정 id.
    - `user_id` : 해당 템플릿을 저장하고자 하는 메일러 계정 id.
- **Request Body**:
    
    ```jsx
    {
      "sub_category": "서브 카테고리",
      "topic": "템플릿 이름",
      "template_title": "주간 업무 보고",
      "template_content": "주간 업무 보고 드립니다."
    }
    ```
    
- **Success Response**: `201 Created`
- **Error Response**:
    - `400 Bad Request`: request body의 일부 필드가 없거나 비어있을 때.
    - `403 Forbidden`:  요청한 계정이 내 소유가 아닐 때.
    - `404 Not Found`:  해당 계정을 찾을 수 없을 때.

### 6.6. 내 템플릿 수정 (구현 완)

```jsx
PATCH /api/template/mytemplate/{template_id}/
```

- **설명**: 특정 이메일 계정(`account_id`)에 속한 특정 템플릿(`template_id`)을 수정한다. db 구조상 template_id는 고유한 값이라 account_id의 구분은 딱히 필요없음.
- **Request Body**: (일부 필드만 전송)
    
    ```jsx
    {
      "sub_category": "서브 카테고리",
      "topic": "템플릿 이름",
      "template_title": "월간 업무 보고",
      "template_content": "월간 업무 보고 드립니다."
    }
    ```
    
- **Success Response**: `200 OK`
- `400 Bad Request`: request body의 일부 필드가 없거나 비어있을 때.
- `403 Forbidden`:  요청한 계정이 내 소유가 아닐 때.
- `404 Not Found`:  해당 템플릿을 찾을 수 없을 때.

### 6.7. 내 템플릿 삭제 (구현 완)

```jsx
DELETE /api/template/mytemplate/{template_id}/
```

- **설명**: 특정 이메일 계정(`account_id`)에 속한 특정 템플릿(`template_id`)을 삭제한다.
- **Success Response**: `204 No Content`
- `403 Forbidden`:  요청한 계정이 내 소유가 아닐 때.
- `404 Not Found`:  해당 템플릿을 찾을 수 없을 때.

## 질문 및 제안

메일 보내도록 하는 api도 필요함 ← 임시로 추가함. request field 어떻게 해야할지는 잘 몰루..

메일 받아서 스팸 처리까지 돌리는건 다 백그라운드인거지? — YES.

메일들을 불러올 때, 첨부파일을 프론트로 다시 보내주는 방법도 생각해봐야할듯. ← 일단 확인. 아직 명세서에 반영은 안함. 프론트에 파일의 s3서버 URL을 전달하는 방식 생각중.

고생하셨습니다~~~~!!