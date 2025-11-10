import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.output_parsers import StructuredOutputParser, ResponseSchema, RetryWithErrorFixingParser
from langchain_core.prompts import PromptTemplate
from langchain import LLMChain
from utils.prompts.prompt import prompt_text

# 스팸메일 처리 로직 피드백.
# 정확도로 하려면 있는 태그들 중 하나를 골라서 집어넣어달라고 지시를 주면 그게 좋을 것 같다.
# 개별 메일 단위로 iteration하고 검증용 요청도 하나 보내놓는 거 좋아보임.

response_schemas = [
    ResponseSchema(
        name="classification",
        description='A JSON object mapping each email "id" (string) to "spam" or "inbox". Example: {"101": "inbox", "102": "spam"}',
    )
]

structured_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = structured_parser.get_format_instructions()


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

    spam_filter_prompt = PromptTemplate.from_template(prompt_text)

    # LLM 초기화
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=0,
            google_api_key=api_key,
        )

        # JSON 형식 오류 자동 수정 파서
        retry_parser = RetryWithErrorFixingParser.from_llm(
            parser=structured_parser,
            llm=llm,
        )

        chain = LLMChain(
            llm=llm,
            prompt=spam_filter_prompt,
            output_parser=retry_parser,  # 🚀 자동 복구 파서 연결
            output_key="classification",
        )

        # LLM 프롬프트에 포함시키기 위해 이메일 리스트를 JSON 문자열로 변환
        emails_json_string = json.dumps(emails, indent=2, ensure_ascii=False)

        result = chain.invoke(
            {
                "job": job,
                "interests": ", ".join(interests),
                "usage": usage,
                "emails": emails_json_string,
            }
        )

        # 결과에서 분류 결과 추출
        classification_results = result.get("classification", {})
        return classification_results
    except Exception as e:
        print(f"Error during email classification: {e}")
        return {}
