import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

load_dotenv()

from analyzer import analyze_weather
from maintenance_store import (
    extract_source_ids,
    get_maintenance_history_by_source_ids,
    log_maintenance_case,
)
from scenarios import WEATHER_SCENARIOS
from swmm_formatter import build_analysis_payload
from telegram_notifier import send_analysis_message

logger = logging.getLogger(__name__)

app = FastAPI()
api = APIRouter()
LLM_API_PREFIX = os.getenv("LLM_API_PREFIX", "/llm").strip() or "/llm"
if not LLM_API_PREFIX.startswith("/"):
    LLM_API_PREFIX = f"/{LLM_API_PREFIX}"
LLM_API_PREFIX = LLM_API_PREFIX.rstrip("/")


@api.get("/health")
async def health():
    return {"status": "ok"}


class AnalyzeBaseRequest(BaseModel):
    id: str
    swmm_raw_data: str

    @field_validator("swmm_raw_data", mode="before")
    @classmethod
    def normalize_swmm_raw_data(cls, value: object) -> str:
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        if value is None:
            raise ValueError("swmm_raw_data는 필수입니다.")
        return str(value)


class AnalyzeRequest(AnalyzeBaseRequest):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: list[str]

    @field_validator("TELEGRAM_CHAT_ID", mode="before")
    @classmethod
    def normalize_chat_ids(cls, value: object) -> list[str]:
        if value is None:
            raise ValueError("TELEGRAM_CHAT_ID는 필수입니다.")
        if isinstance(value, (str, int)):
            return [str(value)]
        if isinstance(value, list):
            return [str(chat_id) for chat_id in value if str(chat_id).strip()]
        raise ValueError("TELEGRAM_CHAT_ID는 문자열 배열이어야 합니다.")


class MaintenanceEvent(BaseModel):
    id: int | str
    run_id: str | None = None
    step_index: int | str | None = None
    model_time: str | None = None
    target_id: str
    source: str | None = None
    hazard_type: str | None = None
    hazard_level: str | None = None
    hazard_detail: str | None = None
    created_at: str | None = None


class MaintenanceAction(BaseModel):
    status: str | None = None
    initial_action_detail: str | None = None
    action_type: str | None = None
    result_detail: str | None = None
    result_status: str | None = None
    recurrence_note: str | None = None
    created_at: str | None = None


class MaintenanceLogRequest(BaseModel):
    event: MaintenanceEvent
    metrics: dict[str, Any] = Field(default_factory=dict)
    action: MaintenanceAction


def _attach_past_history(analysis_input: dict) -> dict:
    source_ids = extract_source_ids(analysis_input)
    analysis_input["past_history"] = get_maintenance_history_by_source_ids(source_ids)
    return analysis_input


def _build_context_summary(analysis_input: dict) -> dict:
    return {
        "hasLinkData": bool(analysis_input.get("link")),
        "hasNodeData": bool(analysis_input.get("node")),
        "hasEditorObjectData": bool(analysis_input.get("editorObject")),
        "linkCount": len(analysis_input.get("link", [])),
        "nodeCount": len(analysis_input.get("node", [])),
        "editorObjectCount": len(analysis_input.get("editorObject", [])),
        "issueCount": len(analysis_input.get("swmmIssues", [])),
        "link": analysis_input.get("link", []),
        "node": analysis_input.get("node", []),
        "editorObject": analysis_input.get("editorObject", []),
        "pastHistoryCount": len(analysis_input.get("past_history", [])),
        "past_history": analysis_input.get("past_history", []),
    }


@app.post("/maintenance/log")
async def maintenance_log(request: MaintenanceLogRequest):
    try:
        result = log_maintenance_case(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"유지보수 기록 저장에 실패했습니다: {exc}",
        ) from exc

    return result


@api.post("/analyze/preview")
async def analyze_preview(request: AnalyzeBaseRequest):
    """LLM 호출 없이 정형화된 입력 payload만 확인합니다."""
    scenario_data = WEATHER_SCENARIOS.get(request.id)
    if scenario_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"존재하지 않는 시나리오입니다. 사용 가능: {list(WEATHER_SCENARIOS)}",
        )

    try:
        analysis_input = build_analysis_payload(
            request.id,
            scenario_data,
            request.swmm_raw_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis_input = _attach_past_history(analysis_input)

    return {
        "id": request.id,
        "contextSummary": _build_context_summary(analysis_input),
        "llmInput": analysis_input,
    }


@api.post("/analyze")
async def analyze(request: AnalyzeRequest):
    scenario_data = WEATHER_SCENARIOS.get(request.id)
    if scenario_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"존재하지 않는 시나리오입니다. 사용 가능: {list(WEATHER_SCENARIOS)}",
        )

    try:
        analysis_input = build_analysis_payload(
            request.id,
            scenario_data,
            request.swmm_raw_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    context_summary = _build_context_summary(analysis_input)
    logger.info("LLM analysis input summary: %s", context_summary)

    if context_summary["issueCount"] == 0 and context_summary["linkCount"] == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "SWMM 데이터 정형화에 실패했습니다. "
                "triggeredIssues 또는 dispatchKey에서 link/node/editor object를 생성하지 못했습니다."
            ),
        )

    analysis_input = _attach_past_history(analysis_input)
    context_summary = _build_context_summary(analysis_input)

    analysis = analyze_weather(analysis_input)

    try:
        sent_to = await send_analysis_message(
            request.id,
            analysis,
            bot_token=request.TELEGRAM_BOT_TOKEN,
            chat_ids=request.TELEGRAM_CHAT_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"텔레그램 메시지 전송에 실패했습니다: {exc}",
        ) from exc

    return {
        "id": request.id,
        "analysis": analysis,
        "contextSummary": context_summary,
        "telegram": {
            "sentTo": sent_to,
            "sentCount": len(sent_to),
        },
    }


app.include_router(api, prefix=LLM_API_PREFIX)
