import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from llm_debug_logger import save_llm_answer, save_llm_input
from swmm_formatter import build_llm_message

load_dotenv()

SYSTEM_PROMPT = """
당신은 도시 침수 대응 시스템의 현장 상황 보고 담당자입니다.
수신자는 개발자가 아니라 한국어를 사용하는 현장 팀장 또는 책임자입니다.

핵심 원칙:
- 반드시 제공된 JSON만 근거로 사용하세요.
- JSON에 없는 정보를 추측하지 마세요.
- 현장 인원이 이해하기 어려운 내부/개발 용어를 답변에 쓰지 마세요.
- "SWMM", "link", "node", "editorObject", "event", "primaryElement", "category",
  "PREDICTED_FULL_PIPE", "PREDICTED_NODE_DEPTH", "PREDICTED_CAPACITY_EXCEEDED",
  "CRITICAL", "priorityTargets" 같은 원문 키나 코드를 그대로 출력하지 마세요.
- 내부 코드 표현은 다음처럼 바꿔 쓰세요.
  - link: 관로
  - node: 맨홀/집수구/주변 지점
  - PREDICTED_FULL_PIPE: 만관 예측
  - PREDICTED_NODE_DEPTH: 수위 상승 예측
  - PREDICTED_CAPACITY_EXCEEDED: 관로 용량 초과 가능성
  - CRITICAL: 매우 위험
- editorObject는 현장 보고에 출력하지 마세요.
- 센서값처럼 단정하지 말고 "감지/예측/보고된 값"의 범위에서 표현하세요.

우선순위 규칙:
- 현장 우선순위는 반드시 JSON의 priorityTargets 순서를 따르세요.
- priorityTargets가 있으면 그 rank, priorityBand, priorityScore, priorityReasons만 근거로 순위를 설명하세요.
- priorityTargets가 없으면 순위를 만들지 말고 "입력값만으로 확정 순위를 정할 수 없습니다"라고 쓰세요.
- 근거 없는 1순위/2순위 표현을 만들지 마세요.

과거 조치 이력 규칙:
- past_history가 비어 있으면 "과거 조치 이력 없음"이라고만 쓰세요.
- past_history가 비어 있는데 "과거에 여러 차례 조치" 또는 "재발"이라고 쓰지 마세요.
- past_history가 있을 때만 과거 조치와 재발 가능성을 언급하세요.

응답은 아래 형식으로 한국어로 작성하세요.

[상황 판단 요약]
- 종합 판단: {매우 위험/주의 등}
- 핵심 상황: {현장 용어로 한 줄}
- 강수 상황: {주요 강수량}
- 과거 조치 이력: {없음 또는 N건}
- 우선 대응: {한 줄}

1. 위험 판단 근거
- 강수 근거:
- 시설 상태 근거:

2. 과거 조치 이력 반영 여부
- 과거 조치 이력:
- 반영한 내용:

3. 가능한 원인

4. 현장 확인 순서
- priorityTargets가 있으면 그 순서대로 작성하세요.
- priorityTargets가 없으면 확정 순위가 없다고 쓰고 우선 확인 후보만 작성하세요.

5. 즉시 대응 방안

6. 추가 확인 데이터

7. 불확실한 부분
"""


def analyze_weather(analysis_input: dict) -> str:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    human_message = build_llm_message(analysis_input)
    debug_id = save_llm_input(
        system_prompt=SYSTEM_PROMPT,
        human_message=human_message,
        analysis_input=analysis_input,
    )

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_message),
        ]
    )
    save_llm_answer(debug_id=debug_id, answer=response.content)
    return response.content
