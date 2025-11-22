import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


def summarize_email_content(subject: str, body: str, is_html: bool = False) -> str:
    """
    주어진 이메일 제목과 본문을 사용하여 LLM에게 요약을 요청합니다.

    Args:
        subject (str): 이메일 제목
        body (str): 이메일 본문
        is_html (bool): 본문이 HTML 형식인지 여부. True이면 HTML 처리 지침이 추가됩니다.

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
        Summarized content should be within 250 korean characters, including spaces.
        """

        if is_html:
            system_instruction += """
            The email body is provided in HTML format. You must first extract the meaningful text content from the HTML, ignoring tags, styles, and scripts.
            If the HTML contains no discernible text and seems to be composed only of images or tracking pixels, analyze them and state proper summary.
            After extracting the text, create the summary.
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
