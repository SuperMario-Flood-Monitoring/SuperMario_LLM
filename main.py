from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from analyzer import analyze_weather
from scenarios import WEATHER_SCENARIOS
from telegram_notifier import send_analysis_message

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


class AnalyzeRequest(BaseModel):
    id: str


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    scenario_data = WEATHER_SCENARIOS.get(request.id)
    if scenario_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"존재하지 않는 시나리오입니다. 사용 가능: {list(WEATHER_SCENARIOS)}",
        )

    analysis = analyze_weather(scenario_data)

    try:
        await send_analysis_message(request.id, analysis)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"텔레그램 메시지 전송에 실패했습니다: {exc}",
        ) from exc

    return {
        "id": request.id,
        "analysis": analysis,
    }
