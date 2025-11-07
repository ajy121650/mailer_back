import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types


def classify_emails_in_batch(emails: list, job: str, interests: list, usage: str) -> dict:
    """
    여러 이메일과 사용자 선호도를 LLM에 한 번에 보내어 스팸 여부를 분류합니다.

    Args:
        emails (list): 각 요소가 {'id': str, 'subject': str, 'body': str} 형태인 딕셔너리 리스트
        job (str): 사용자의 직업
        interests (list): 사용자의 관심사 키워드 리스트
        usage (str): 계정의 용도

    Returns:
        dict: 이메일 ID를 키로, 'spam' 또는 'inbox'를 값으로 갖는 딕셔너리
    """
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file")
        return {}

    try:
        client = genai.Client(api_key=api_key)

        system_instruction = """
        You are a highly intelligent spam classification expert. Your task is to classify a list of emails as either "spam" or "inbox" based on the user's personal and professional context.

        I will provide you with:
        1.  **User Profile:** Their job, interests, and how they use the email account.
        2.  **Emails:** A JSON array of emails, each with an ID, subject, and body.

        **Classification Guidelines:**
        -   **inbox:** Emails that are relevant to the user's job, studies, stated interests, or appear to be important personal or professional communication.
        -   **spam:** Unsolicited promotional emails, scams, newsletters the user didn't subscribe to, or content completely irrelevant to their profile.

        **Output Format:**
        Your response MUST be a single, valid JSON object. The keys must be the string email IDs, and the values must be the classification string: "spam" or "inbox".

        **Example:**
        -   **Input (in user prompt):**
            User Profile:
            - Job: "Software Engineer"
            - Interests: ["Python", "Django"]
            - Usage: "Work"
            Emails:
            [{"id": "101", "subject": "New Python library released!", "body": "..."}, {"id": "102", "subject": "Buy cheap watches", "body": "..."}]
        -   **Your Output:**
            {
              "101": "inbox",
              "102": "spam"
            }

        Do not output any other text, explanations, or markdown formatting. Just the JSON object.
        """
        # 1. 청크 단위 줄이기 2. 스팸에 대한 정의가 모호하다. 오히려 JSON 포맷으로 가능한 토픽 20개 정도 주루룩 늘여놓고 마지막에 이것도 다 아니면 스팸메일로 처리. 이 카테고리 중 하나로 분류해줘.
        # 그리고 매 메일마다 iteration 돌리기. 기존에 spam으로 된거 유지하는 것도 괜찮아보이는데.

        # LLM 프롬프트에 포함시키기 위해 이메일 리스트를 JSON 문자열로 변환
        emails_json_string = json.dumps(emails, indent=2, ensure_ascii=False)

        user_prompt = f"""
        **User Profile:**
        - Job: {job}
        - Interests: {interests}
        - Usage: {usage}

        **Emails to Classify:**
        {emails_json_string}
        """

        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = client.models.generate_content(model="gemini-2.5-pro", config=config, contents=user_prompt)

        # LLM의 응답에서 JSON 부분만 추출
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()

        # JSON 응답을 파싱하여 딕셔너리로 변환
        classification_results = json.loads(cleaned_response)
        return classification_results

    except Exception as e:
        print(f"An error occurred during the batch classification API call: {e}")
        return {}


# 스팸메일 처리 로직 피드백.
# 정확도로 하려면 있는 태그들 중 하나를 골라서 집어넣어달라고 지시를 주면 그게 좋을 것 같다.
# 개별 메일 단위로 iteration하고 검증용 요청도 하나 보내놓는 거 좋아보임.
