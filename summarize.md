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