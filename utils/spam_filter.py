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
        dict: 이메일 ID를 키로, 'junk' 또는 'inbox'를 값으로 갖는 딕셔너리
    """
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file")
        return {}

    try:
        client = genai.Client(api_key=api_key)

        system_instruction = '''
        You are a spam classification expert. I will provide you with a user's preferences (job, interests, usage) and a list of emails in a JSON array format.
        Your task is to classify each email as either "junk" or "inbox".
        Your response MUST be a single, valid JSON object where the keys are the email IDs (as strings) and the values are the classification strings ("junk" or "inbox").
        Do not output any other text, explanations, or markdown formatting.
        '''

        # LLM 프롬프트에 포함시키기 위해 이메일 리스트를 JSON 문자열로 변환
        emails_json_string = json.dumps(emails, indent=2, ensure_ascii=False)

        user_prompt = f"""
        Here are the user's preferences and the list of emails to classify.

        **User Preferences:**
        - 직업: {job}
        - 관심사: {interests}
        - 계정의 용도: {usage}

        **Emails to Classify (JSON Array):**
        {emails_json_string}

        Please classify these emails and return a single JSON object mapping each email ID to its classification ("junk" or "inbox").
        """

        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            config=config,
            contents=user_prompt
        )

        # LLM의 응답에서 JSON 부분만 추출
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        
        # JSON 응답을 파싱하여 딕셔너리로 변환
        classification_results = json.loads(cleaned_response)
        return classification_results

    except Exception as e:
        print(f"An error occurred during the batch classification API call: {e}")
        return {}
