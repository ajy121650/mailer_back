import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import ValidationError

from utils.prompts.prompt import prompt_text, repair_prompt_text

from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END

# utils/spam_schemas.py
from typing import Literal
from pydantic import BaseModel, Field

# 스팸메일 처리 로직 피드백.
# 정확도로 하려면 있는 태그들 중 하나를 골라서 집어넣어달라고 지시를 주면 그게 좋을 것 같다.
# 개별 메일 단위로 iteration하고 검증용 요청도 하나 보내놓는 거 좋아보임.


# -------------------- State 정의 --------------------
class SpamState(TypedDict, total=False):
    job: str
    interests: List[str]
    usage: str
    emails: List[Dict[str, Any]]
    result: Dict[str, str]
    error: Optional[str]
    raw_text: Optional[str]


# -------------------- Pydantic Structured Schema --------------------
class ClassificationResult(BaseModel):
    """email_id -> 'spam' | 'inbox'"""

    classification: Dict[str, Literal["spam", "inbox"]] = Field(
        ..., description="Mapping from email id (string) to label ('spam' or 'inbox')."
    )


# -------------------- classify_node --------------------
def classify_node(state: SpamState) -> SpamState:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not found"}

    classify_prompt = PromptTemplate.from_template(prompt_text)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",  # flash 모델은 더 빠르고 quota가 넉넉함
        temperature=0,
        google_api_key=api_key,
    ).with_structured_output(ClassificationResult)

    chain = classify_prompt | llm

    try:
        emails_json = json.dumps(state["emails"], indent=2, ensure_ascii=False)
        output = chain.invoke(
            {
                "job": state["job"],
                "interests": ", ".join(state["interests"]),
                "usage": state["usage"],
                "emails": emails_json,
            }
        )
        return {"result": output.classification}
    except ValidationError as ve:
        return {"error": f"ValidationError: {ve}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# -------------------- repair_node --------------------
def repair_node(state: SpamState) -> SpamState:
    """LLM 출력이 깨졌을 때 유연한 재시도"""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not found"}

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",  # flash 모델은 더 빠르고 quota가 넉넉함
        temperature=0,
        google_api_key=api_key,
    )

    repair_prompt = PromptTemplate.from_template(repair_prompt_text)

    chain = repair_prompt | llm | StrOutputParser()

    try:
        emails_json = json.dumps(state["emails"], indent=2, ensure_ascii=False)
        raw = chain.invoke(
            {
                "job": state["job"],
                "interests": ", ".join(state["interests"]),
                "usage": state["usage"],
                "emails": emails_json,
            }
        ).strip()

        cleaned = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        return {"result": parsed.get("classification", parsed), "raw_text": raw}
    except Exception as e:
        return {"error": f"RepairFailed: {type(e).__name__}: {e}"}


# -------------------- 조건부 분기 --------------------
def route_on_error(state: SpamState) -> str:
    return "repair" if state.get("error") else END


# -------------------- 그래프 구성 --------------------
def build_spam_graph():
    graph = StateGraph(SpamState)
    graph.add_node("classify", classify_node)
    graph.add_node("repair", repair_node)
    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", route_on_error, {"repair": "repair", END: END})
    graph.add_edge("repair", END)
    return graph.compile()


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
    app = build_spam_graph()
    state = {"emails": emails, "job": job, "interests": interests, "usage": usage}
    final_state = app.invoke(state)

    return final_state.get("result", {})
