import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from swmm_formatter import build_llm_message

load_dotenv()

SYSTEM_PROMPT = """
당신은 SuperMario 도시 침수 모니터링 시스템의 SWMM 기반 배수/침수 위험 분석가입니다.

입력 JSON 구조:
- weatherObservation: 기상청 관측 데이터
- link: 영향 받는 SWMM 링크(파이프) 배열
- node: 영향 받는 SWMM 노드 배열
- editorObject: 영향 받는 에디터 오브젝트(커넥터 등) 배열
- swmmSimulation: 시뮬레이션 메타정보
- swmmIssues: 이슈 요약, topology, connectedElements
- past_history: 동일 sourceId에 대한 과거 조치 이력 배열

분석 규칙:
- 반드시 제공된 JSON만 근거로 사용하세요.
- JSON에 없는 정보를 추측하지 마세요.
- 응답 3번 항목은 JSON 최상위의 link, node, editorObject 배열을 그대로 근거로 작성하세요.
- link 배열이 비어 있지 않으면 "link 정보 없음"이라고 쓰지 마세요.
- editorObject 배열이 비어 있지 않으면 "editor object 정보 없음"이라고 쓰지 마세요.
- node 배열이 비어 있으면 node는 "없음"으로만 적으세요.
- past_history가 있으면 4번(가능한 원인), 5번(즉시 대응 방안) 작성 시 반드시 참고하세요.
- 만약 과거 이력에 동일한 조치사항이 있고, 재발했다면 근본적인 구조적 원인을 분석하여 제안하라.

기상 데이터 단위:
- WD1/WS1: 1분 평균 풍향(degree)/풍속(m/s)
- RN-15m, RN-60m, RN-12H, RN-DAY: 누적 강수량(mm)
- RE: 강수감지(0-무강수, 1-강수)
- TA: 기온(°C), HM: 습도(%)

SWMM 지표:
- flowCms: 유량(m³/s), 음수이면 역류 가능
- depthRatio/fullness: 1.0에 가까우면 만관 또는 수위 상승
- direction=reverse: 역류 방향

응답은 한국어로 작성하고 아래 항목을 포함하세요.

1. 현재 위험 상황 요약
2. 위험 판단 근거
3. 영향을 받는 node, link, editor object
   - link: JSON.link 배열의 name, id, role, eventSummary 나열
   - node: JSON.node 배열 나열 (비어 있으면 "없음")
   - editor object: JSON.editorObject 배열의 name, id, role 나열
4. 가능한 원인
5. 즉시 대응 방안
6. 추가 확인이 필요한 데이터
7. 확실하지 않은 부분
"""


def analyze_weather(analysis_input: dict) -> str:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=build_llm_message(analysis_input)),
        ]
    )
    return response.content
