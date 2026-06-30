import os
import uuid
from datetime import datetime, timezone
from typing import Any

import chromadb
from langchain_openai import OpenAIEmbeddings

COLLECTION_NAME = "maintenance_logs"

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_embeddings: OpenAIEmbeddings | None = None


def _get_persist_dir() -> str:
    return os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")


def _get_collection() -> tuple[chromadb.Collection, OpenAIEmbeddings]:
    global _client, _collection, _embeddings

    if _collection is None or _embeddings is None:
        _client = chromadb.PersistentClient(path=_get_persist_dir())
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    return _collection, _embeddings


def extract_source_ids(analysis_input: dict[str, Any]) -> list[str]:
    source_ids: list[str] = []
    seen: set[str] = set()

    for item in analysis_input.get("link", []):
        element_id = item.get("id")
        if element_id and element_id not in seen:
            seen.add(element_id)
            source_ids.append(str(element_id))

    for issue in analysis_input.get("swmmIssues", []):
        primary = issue.get("primaryElement") or {}
        element_id = primary.get("id")
        if element_id and element_id not in seen:
            seen.add(element_id)
            source_ids.append(str(element_id))

    return source_ids


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _format_percent(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return _string_or_none(value)
    return f"{value * 100:.1f}%"


def _format_metric_line(label: str, value: Any, unit: str = "") -> str | None:
    if value is None or value == "":
        return None
    return f"- {label}: {value}{unit}"


def format_maintenance_case(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    metrics = payload.get("metrics") or {}
    action = payload.get("action") or {}

    if not isinstance(event, dict):
        raise ValueError("event는 객체여야 합니다.")
    if not isinstance(metrics, dict):
        raise ValueError("metrics는 객체여야 합니다.")
    if not isinstance(action, dict):
        raise ValueError("action은 객체여야 합니다.")

    source_id = _string_or_none(event.get("target_id"))
    if not source_id:
        raise ValueError("event.target_id는 필수입니다.")

    action_text_parts = [
        _string_or_none(action.get("initial_action_detail")),
        _string_or_none(action.get("result_detail")),
    ]
    action_text = "\n".join(part for part in action_text_parts if part)
    if not action_text:
        raise ValueError("action.initial_action_detail 또는 action.result_detail은 필수입니다.")

    metric_lines = [
        _format_metric_line("유량", metrics.get("flowCms"), " m3/s"),
        _format_metric_line("흐름 방향", metrics.get("direction")),
        _format_metric_line("만관율", _format_percent(metrics.get("fullness"))),
        _format_metric_line("용량 비율", _format_percent(metrics.get("capacityRatio"))),
        _format_metric_line("막힘 비율", _format_percent(metrics.get("blockageRatio"))),
        _format_metric_line("수위 비율", _format_percent(metrics.get("depthRatio"))),
        _format_metric_line("침수 유량", metrics.get("floodingCms"), " m3/s"),
    ]
    metric_lines = [line for line in metric_lines if line]

    lines = [
        "[도시침수 위험 대응 사례]",
        "",
        f"이벤트 ID: {_string_or_none(event.get('id')) or '미상'}",
        f"시설 ID: {source_id}",
        f"시설 유형: {_string_or_none(event.get('source')) or '미상'}",
        f"위험 유형: {_string_or_none(event.get('hazard_type')) or '미상'}",
        f"위험 등급: {_string_or_none(event.get('hazard_level')) or '미상'}",
    ]

    hazard_detail = _string_or_none(event.get("hazard_detail"))
    if hazard_detail:
        lines.append(f"위험 상세: {hazard_detail}")

    lines.extend(
        [
            f"발생 시각: {_string_or_none(event.get('created_at')) or '미상'}",
            f"모델 시각: {_string_or_none(event.get('model_time')) or '미상'}",
            f"실행 ID: {_string_or_none(event.get('run_id')) or '미상'}",
            f"스텝: {_string_or_none(event.get('step_index')) or '미상'}",
        ]
    )

    priority = event.get("priority") if isinstance(event.get("priority"), dict) else {}
    if priority:
        reasons = priority.get("priorityReasons")
        reason_text = ", ".join(str(reason) for reason in reasons) if isinstance(reasons, list) else ""
        lines.extend(
            [
                "",
                "현장 조치 우선순위:",
                f"- 등급: {_string_or_none(priority.get('priorityBand')) or '미상'}",
                f"- 점수: {_string_or_none(priority.get('priorityScore')) or '미상'}",
                f"- 근거: {reason_text or '없음'}",
            ]
        )

    lines.extend(
        [
            "",
            "주요 지표:",
        ]
    )

    lines.extend(metric_lines or ["- 없음"])
    lines.extend(["", "조치:"])

    action_status = _string_or_none(action.get("status"))
    action_type = _string_or_none(action.get("action_type"))
    result_status = _string_or_none(action.get("result_status"))
    if action_status:
        lines.append(f"- 상태: {action_status}")
    if action_type:
        lines.append(f"- 조치 유형: {action_type}")
    if _string_or_none(action.get("initial_action_detail")):
        lines.append(f"- 초기 조치: {action.get('initial_action_detail')}")
    if _string_or_none(action.get("result_detail")):
        lines.append(f"- 결과: {action.get('result_detail')}")
    if result_status:
        lines.append(f"- 결과 상태: {result_status}")
    if _string_or_none(action.get("created_at")):
        lines.append(f"- 조치 시각: {action.get('created_at')}")

    recurrence_note = _string_or_none(action.get("recurrence_note"))
    lines.extend(["", "재발 시 참고사항:", recurrence_note or "없음"])

    return "\n".join(lines)


def log_maintenance_case(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event") or {}
    action = payload.get("action") or {}
    formatted_text = format_maintenance_case(payload)
    source_id = str(event["target_id"]).strip()

    collection, embeddings = _get_collection()
    log_id = str(uuid.uuid4())
    logged_at = datetime.now(timezone.utc).isoformat()
    vector = embeddings.embed_query(formatted_text)

    metadata = {
        "sourceId": source_id,
        "loggedAt": logged_at,
        "eventId": str(event.get("id", "")),
        "hazardType": str(event.get("hazard_type", "")),
        "hazardLevel": str(event.get("hazard_level", "")),
        "actionStatus": str(action.get("status", "")),
        "resultStatus": str(action.get("result_status", "")),
    }
    priority = event.get("priority") if isinstance(event.get("priority"), dict) else {}
    if priority:
        metadata["priorityBand"] = str(priority.get("priorityBand", ""))
        metadata["priorityScore"] = str(priority.get("priorityScore", ""))

    collection.add(
        ids=[log_id],
        embeddings=[vector],
        documents=[formatted_text],
        metadatas=[metadata],
    )

    return {
        "id": log_id,
        "vector_id": log_id,
        "sourceId": source_id,
        "action_details": formatted_text,
        "embedding_text": formatted_text,
        "loggedAt": logged_at,
    }


def log_maintenance_action(source_id: str, action_details: str) -> dict[str, Any]:
    normalized_source_id = source_id.strip()
    normalized_action = action_details.strip()

    if not normalized_source_id:
        raise ValueError("sourceId는 필수입니다.")
    if not normalized_action:
        raise ValueError("action_details는 필수입니다.")

    collection, embeddings = _get_collection()
    log_id = str(uuid.uuid4())
    logged_at = datetime.now(timezone.utc).isoformat()
    vector = embeddings.embed_query(normalized_action)

    collection.add(
        ids=[log_id],
        embeddings=[vector],
        documents=[normalized_action],
        metadatas=[{"sourceId": normalized_source_id, "loggedAt": logged_at}],
    )

    return {
        "id": log_id,
        "sourceId": normalized_source_id,
        "action_details": normalized_action,
        "loggedAt": logged_at,
    }


def get_maintenance_history_by_source_ids(source_ids: list[str]) -> list[dict[str, Any]]:
    if not source_ids:
        return []

    collection, _ = _get_collection()
    history: list[dict[str, Any]] = []
    seen_log_ids: set[str] = set()

    for source_id in source_ids:
        results = collection.get(
            where={"sourceId": source_id},
            include=["documents", "metadatas"],
        )

        ids = results.get("ids") or []
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []

        for log_id, document, metadata in zip(ids, documents, metadatas):
            if log_id in seen_log_ids:
                continue
            seen_log_ids.add(log_id)

            metadata = metadata or {}
            history.append(
                {
                    "id": log_id,
                    "sourceId": metadata.get("sourceId", source_id),
                    "action_details": document,
                    "loggedAt": metadata.get("loggedAt"),
                }
            )

    history.sort(key=lambda item: item.get("loggedAt") or "", reverse=True)
    return history
