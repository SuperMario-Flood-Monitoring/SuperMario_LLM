import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()

SYSTEM_PROMPT = (
    "너는 배관망 유지보수 전문가야. "
    "제공된 기상청 관측 데이터(YYMMDDHHMI, STN, WD1/WS1, WDS/WSS, WD10/WS10, TA, RE, "
    "RN-15m, RN-60m, RN-12H, RN-DAY, HM, PA, PS, TD)를 분석해. "
    "현재 날씨 상황을 요약하고, 침수 예방을 위한 조치 사항을 1문장으로 제안해."
)


def analyze_weather(scenario_data: dict) -> str:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(scenario_data, ensure_ascii=False)),
        ]
    )
    return response.content
