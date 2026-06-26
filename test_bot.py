import asyncio
import os

import httpx
from dotenv import load_dotenv
from telegram import Bot

from telegram_notifier import discover_chat_id, format_analysis_message

load_dotenv()

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8001/llm/analyze")

SAMPLE_SWMM_RAW = """
{
  "loggedAt": "2026-06-24T12:27:51.219",
  "status": "scheduled",
  "runId": "20260624-122709-3bfc7bc5",
  "stepIndex": 333,
  "modelTime": "2026-06-16T00:05:33",
  "reason": "new_issue",
  "highestSeverity": "CRITICAL",
  "riskEventCount": 4,
  "triggeredIssues": [
    {
      "issueId": "REVERSE_FLOW:link:pipe_free_1781771885636",
      "eventType": "REVERSE_FLOW",
      "severity": "CRITICAL",
      "sourceId": "pipe_free_1781771885636",
      "displayName": "파이프",
      "fromNode": "teeConnector_copy_1781771853047_1",
      "fromNodeName": "T자 커넥터 102 복사 복사",
      "toNode": "CONN_COMB_01",
      "toNodeName": "합류식 커넥터 01"
    }
  ]
}
"""


async def setup_chat_id():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN을 .env에 먼저 설정하세요.")
        return

    chat_id = await discover_chat_id()
    if chat_id is None:
        print("메시지를 찾지 못했습니다. 봇에게 /start 를 보낸 뒤 다시 실행하세요.")
        return

    bot = Bot(token=token)
    await bot.send_message(
        chat_id=chat_id,
        text=format_analysis_message("테스트", "봇 연결 성공! 이제 침수 예보를 보낼 수 있어요."),
    )

    print(f"채팅방 ID: {chat_id}")
    print("Django 요청의 TELEGRAM_CHAT_ID 배열에 아래 값을 넣으세요:")
    print(f'["{chat_id}"]')


async def test_analyze_api(scenario_id: str = "폭우"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FASTAPI_URL,
            json={
                "id": scenario_id,
                "swmm_raw_data": SAMPLE_SWMM_RAW,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

    print("API 응답:")
    print(result)
    print("\n/analyze 호출 시 텔레그램으로도 동일한 분석 결과가 전송됩니다.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        asyncio.run(setup_chat_id())
    else:
        asyncio.run(test_analyze_api(sys.argv[1] if len(sys.argv) > 1 else "폭우"))
