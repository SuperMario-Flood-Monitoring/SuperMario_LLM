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
