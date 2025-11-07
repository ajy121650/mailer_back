import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


def summarize_email_content(subject: str, body: str) -> str:
    """
    주어진 이메일 제목과 본문을 사용하여 LLM에게 요약을 요청합니다.

    Args:
        subject (str): 이메일 제목
        body (str): 이메일 본문

    Returns:
        str: LLM이 생성한 요약 내용
    """
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file")
        return ""

    try:
        client = genai.Client(api_key=api_key)

        system_instruction = """
        You are an expert at summarizing emails. Your task is to create a concise summary of the given email content.
        The summary should be in Korean.
        Focus on the main point of the email and be as brief as possible.
        """

        user_prompt = f"""
        **Subject:** {subject}

        **Body:**
        {body}
        """

        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = client.models.generate_content(model="gemini-2.5-pro", config=config, contents=user_prompt)

        return response.text.strip()

    except Exception as e:
        print(f"An error occurred during the summarization API call: {e}")
        return ""
