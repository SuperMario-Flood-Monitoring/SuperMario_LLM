import json
from typing import Any

EVENT_TYPE_LABELS = {
    "REVERSE_FLOW": "역류",
    "OVERFLOW": "범람",
    "SURCHARGE": "만관",
    "BLOCKAGE": "막힘",
    "FLOODING": "침수",
    "HIGH_DEPTH": "수위 상승",
    "LOW_FLOW": "유량 저하",
    "PREDICTED_FULL_PIPE": "만관 예측",
    "PREDICTED_CAPACITY_EXCEEDED": "관로 용량 초과 예측",
    "PREDICTED_NODE_DEPTH": "수위 상승 예측",
    "PREDICTED_FLOODING": "침수 예측",
    "PREDICTED_BLOCKAGE_CLOSED": "막힘 폐쇄 예측",
    "PREDICTED_BLOCKAGE_HIGH": "막힘 증가 예측",
}

SEVERITY_LABELS = {
    "CRITICAL": "치명",
    "HIGH": "높음",
    "MEDIUM": "중간",
    "LOW": "낮음",
    "INFO": "정보",
}

REASON_LABELS = {
    "new_issue": "신규 이슈",
    "escalation": "심각도 상승",
    "periodic": "주기 점검",
}

STATUS_LABELS = {
    "scheduled": "분석 예약",
    "running": "실행 중",
    "completed": "완료",
    "failed": "실패",
}

ROLE_LABELS = {
    "issue_source": "이슈 발생 지점",
    "upstream_endpoint": "상류 연결 지점",
    "downstream_endpoint": "하류 연결 지점",
    "connected_endpoint": "연결 지점",
}

EDITOR_OBJECT_SUBTYPE_LABELS = {
    "tee_connector": "T자 커넥터",
    "combiner_connector": "합류식 커넥터",
    "connector": "커넥터",
    "editor_object": "에디터 오브젝트",
}


def _drop_empty_values(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None and value != ""}


def _parse_issue_id(issue_id: str) -> dict[str, str | None]:
    parts = issue_id.split(":")
    if len(parts) >= 3:
        return {
            "eventType": parts[0],
            "elementCategory": parts[1],
            "elementId": ":".join(parts[2:]),
        }
    if len(parts) == 2:
        return {"eventType": parts[0], "elementCategory": None, "elementId": parts[1]}
    return {"eventType": None, "elementCategory": None, "elementId": issue_id}


def _classify_element(element_id: str, category_hint: str | None = None) -> str:
    if category_hint:
        normalized = category_hint.lower()
        if normalized in {"link", "pipe"}:
            return "link"
        if normalized in {"node", "junction", "outfall"}:
            return "node"
        if normalized in {"editor_object", "editor", "connector"}:
            return "editor_object"

    lowered = element_id.lower()
    if "pipe" in lowered or "conduit" in lowered or lowered.startswith("pipe"):
        return "link"
    if any(token in element_id for token in ("teeconnector", "connector", "conn_")):
        return "editor_object"
    if any(token in lowered for token in ("junction", "outfall", "divider", "storage", "catch_basin")):
        return "node"
    if "node" in lowered:
        return "node"
    return "unknown"


def _editor_object_subtype(element_id: str) -> str:
    lowered = element_id.lower()
    if "teeconnector" in lowered:
        return "tee_connector"
    if "conn_comb" in lowered or "combiner" in lowered:
        return "combiner_connector"
    if "connector" in lowered or "conn_" in lowered:
        return "connector"
    return "editor_object"


def _unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _metric_fields(source: dict[str, Any]) -> dict[str, Any]:
    nested_metrics = source.get("metrics") if isinstance(source.get("metrics"), dict) else {}
    metric_source = {**nested_metrics, **source}
    metrics = _drop_empty_values(
        {
            "metric": metric_source.get("metric"),
            "currentValue": metric_source.get("currentValue"),
            "predictedValue": metric_source.get("predictedValue"),
            "slopePerSecond": metric_source.get("slopePerSecond"),
            "minCurrentValue": metric_source.get("minCurrentValue"),
            "rainfallLevel": metric_source.get("rainfallLevel"),
            "forecastMinutes": metric_source.get("forecastMinutes"),
            "flowCms": metric_source.get("flowCms"),
            "velocityMps": metric_source.get("velocityMps"),
            "depthRatio": metric_source.get("depthRatio"),
            "fullness": metric_source.get("fullness"),
            "capacityRatio": metric_source.get("capacityRatio"),
            "blockageRatio": metric_source.get("blockageRatio"),
            "direction": metric_source.get("direction"),
            "rainfallRatio": metric_source.get("rainfallRatio"),
            "rainfallPercent": metric_source.get("rainfallPercent"),
            "maxRainfallMmPerHour": metric_source.get("maxRainfallMmPerHour"),
            "floodingCms": metric_source.get("floodingCms"),
            "flooded": metric_source.get("flooded"),
            "pondingDepth": metric_source.get("pondingDepth"),
            "invertElevation": metric_source.get("invertElevation"),
        }
    )

    if metrics.get("flowCms") is not None and metrics["flowCms"] < 0:
        metrics["flowDirectionNote"] = "음수 유량 - 역류 가능"
    elif metrics.get("direction") == "reverse":
        metrics["flowDirectionNote"] = "역류 방향"

    return metrics


def _event_brief(issue: dict[str, Any], parsed: dict[str, str | None]) -> dict[str, Any]:
    event_type = issue.get("eventType") or parsed.get("eventType")
    issue_id = issue.get("issueId") or issue.get("eventId")
    return _drop_empty_values(
        {
            "event": EVENT_TYPE_LABELS.get(event_type, event_type),
            "eventCode": event_type,
            "severity": SEVERITY_LABELS.get(issue.get("severity"), issue.get("severity")),
            "severityCode": issue.get("severity"),
            "issueId": issue_id,
        }
    )


def _make_element(
    element_id: str,
    *,
    name: str | None = None,
    category: str | None = None,
    category_hint: str | None = None,
    role: str | None = None,
    event: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    connected_link_ids: list[str] | None = None,
) -> dict[str, Any]:
    resolved_category = category or _classify_element(element_id, category_hint)
    record: dict[str, Any] = {
        "id": element_id,
        "name": name,
        "category": resolved_category,
        "roles": [role] if role else [],
        "relatedEvents": [event] if event else [],
    }

    if resolved_category == "editor_object":
        subtype = _editor_object_subtype(element_id)
        record["editorObjectType"] = subtype
        record["editorObjectTypeLabel"] = EDITOR_OBJECT_SUBTYPE_LABELS.get(subtype, subtype)

    if metrics:
        record["metrics"] = metrics
    if connected_link_ids:
        record["connectedLinkIds"] = connected_link_ids

    return _drop_empty_values(record)


def _merge_element(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    if incoming.get("name") and not target.get("name"):
        target["name"] = incoming["name"]

    for role in incoming.get("roles", []):
        if role not in target.setdefault("roles", []):
            target["roles"].append(role)

    existing_issue_ids = {event.get("issueId") for event in target.setdefault("relatedEvents", [])}
    for event in incoming.get("relatedEvents", []):
        if event.get("issueId") not in existing_issue_ids:
            target["relatedEvents"].append(event)
            existing_issue_ids.add(event.get("issueId"))

    if incoming.get("metrics"):
        target["metrics"] = {**target.get("metrics", {}), **incoming["metrics"]}

    for link_id in incoming.get("connectedLinkIds", []):
        connected = target.setdefault("connectedLinkIds", [])
        if link_id not in connected:
            connected.append(link_id)

    if incoming.get("editorObjectType"):
        target["editorObjectType"] = incoming["editorObjectType"]
        target["editorObjectTypeLabel"] = incoming.get("editorObjectTypeLabel")


def _registry_add(
    registry: dict[str, dict[str, dict[str, Any]]],
    bucket: str,
    element_id: str,
    element: dict[str, Any],
) -> None:
    if element_id not in registry[bucket]:
        registry[bucket][element_id] = element
        return
    _merge_element(registry[bucket][element_id], element)


def _build_topology_description(
    upstream_name: str | None,
    link_name: str | None,
    downstream_name: str | None,
) -> str | None:
    if not any((upstream_name, link_name, downstream_name)):
        return None

    upstream = upstream_name or "상류 지점"
    link = link_name or "링크"
    downstream = downstream_name or "하류 지점"
    return f"{upstream} -> [{link}] -> {downstream}"


def _format_issue_summary(
    issue: dict[str, Any],
    parsed: dict[str, str | None],
    primary_name: str | None,
    primary_id: str | None,
) -> str:
    event = _event_brief(issue, parsed)
    event_label = event.get("event", "이벤트")
    severity_label = event.get("severity", issue.get("severity", "미상"))
    display_name = primary_name or issue.get("displayName") or primary_id or "알 수 없는 요소"
    element_id = primary_id or issue.get("sourceId") or parsed.get("elementId") or "unknown"
    return f"{display_name}({element_id})에서 {event_label}({severity_label}) 발생"


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _band_from_score(score: float) -> str:
    if score >= 85:
        return "P1"
    if score >= 70:
        return "P2"
    if score >= 50:
        return "P3"
    return "P4"


def _extract_priority(issue: dict[str, Any]) -> dict[str, Any] | None:
    score = issue.get("priorityScore")
    band = issue.get("priorityBand")
    reasons = issue.get("priorityReasons")

    if score is None and band is None and reasons is None:
        return None

    normalized_reasons = reasons if isinstance(reasons, list) else []
    return _drop_empty_values(
        {
            "priorityScore": score,
            "priorityBand": band,
            "priorityReasons": [str(reason) for reason in normalized_reasons],
            "source": "django",
        }
    )


def _fallback_priority(issue: dict[str, Any]) -> dict[str, Any]:
    score = 0.0
    reasons: list[str] = []
    severity = issue.get("severityCode") or issue.get("severity")
    event_code = issue.get("eventCode")
    primary = issue.get("primaryElement") or {}
    category = primary.get("category")
    metrics = issue.get("metrics") or {}

    if severity == "CRITICAL" or severity == "치명":
        score += 50
        reasons.append("매우 위험 등급")
    elif severity == "HIGH" or severity == "높음":
        score += 35
        reasons.append("높은 위험 등급")
    elif severity == "WARNING":
        score += 25
        reasons.append("주의 위험 등급")

    event_weights = {
        "PREDICTED_FLOODING": (30, "침수 위험"),
        "OVERFLOW": (30, "월류 위험"),
        "FLOODING": (30, "침수 위험"),
        "PREDICTED_FULL_PIPE": (25, "만관 위험"),
        "PREDICTED_CAPACITY_EXCEEDED": (25, "관로 용량 초과 위험"),
        "SURCHARGE": (25, "만관 위험"),
        "PREDICTED_NODE_DEPTH": (20, "수위 상승 위험"),
        "HIGH_DEPTH": (20, "수위 상승 위험"),
        "REVERSE_FLOW": (20, "역류 위험"),
        "PREDICTED_BLOCKAGE_CLOSED": (20, "막힘 폐쇄 위험"),
        "PREDICTED_BLOCKAGE_HIGH": (15, "막힘 증가 위험"),
        "BLOCKAGE": (15, "막힘 위험"),
    }
    if event_code in event_weights:
        weight, reason = event_weights[event_code]
        score += weight
        reasons.append(reason)

    for metric_name, threshold, weight, reason in (
        ("predictedValue", 0.95, 15, "예측값이 위험 기준에 근접"),
        ("currentValue", 0.9, 10, "현재값이 위험 기준에 근접"),
        ("fullness", 0.95, 15, "만관율 높음"),
        ("capacityRatio", 1.0, 15, "용량 초과"),
        ("depthRatio", 0.9, 12, "수위 비율 높음"),
        ("blockageRatio", 0.8, 12, "막힘 비율 높음"),
    ):
        metric_value = _as_float(metrics.get(metric_name))
        if metric_value is not None and metric_value >= threshold:
            score += weight
            reasons.append(reason)

    flooding_cms = _as_float(metrics.get("floodingCms"))
    if flooding_cms is not None and flooding_cms > 0:
        score += 20
        reasons.append("침수 유량 발생")

    if category == "node":
        score += 5
        reasons.append("현장 침수 접점에 가까운 지점")

    return {
        "priorityScore": round(score, 1),
        "priorityBand": _band_from_score(score),
        "priorityReasons": _unique_list(reasons),
        "source": "fallback",
    }


def _priority_sort_key(target: dict[str, Any]) -> tuple[int, float, str]:
    band_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    score = _as_float(target.get("priorityScore")) or 0.0
    return (
        band_order.get(str(target.get("priorityBand")), 9),
        -score,
        str(target.get("targetId") or ""),
    )


def _build_priority_targets(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []

    for issue in issues:
        primary = issue.get("primaryElement") or {}
        target_id = primary.get("id")
        if not target_id:
            continue

        priority = issue.get("priority") or _fallback_priority(issue)
        targets.append(
            _drop_empty_values(
                {
                    "rank": 0,
                    "targetId": target_id,
                    "targetType": primary.get("category"),
                    "targetName": primary.get("name"),
                    "riskLabel": issue.get("event"),
                    "riskCode": issue.get("eventCode"),
                    "severity": issue.get("severity"),
                    "severityCode": issue.get("severityCode"),
                    "priorityScore": priority.get("priorityScore"),
                    "priorityBand": priority.get("priorityBand"),
                    "priorityReasons": priority.get("priorityReasons") or [],
                    "prioritySource": priority.get("source"),
                    "metrics": issue.get("metrics"),
                }
            )
        )

    targets.sort(key=_priority_sort_key)
    for index, target in enumerate(targets, start=1):
        target["rank"] = index
    return targets


def _extract_issue_elements(
    issue: dict[str, Any],
    parsed: dict[str, str | None],
    event: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_id = issue.get("sourceId") or parsed.get("elementId") or ""
    source_name = issue.get("displayName") or issue.get("sourceEditorName")
    source_category = _classify_element(source_id, issue.get("source") or parsed.get("elementCategory"))
    metrics = _metric_fields(issue)

    primary = _make_element(
        source_id,
        name=source_name,
        category=source_category,
        category_hint=parsed.get("elementCategory"),
        role="issue_source",
        event=event,
        metrics=metrics or None,
    )

    related: list[dict[str, Any]] = []
    endpoint_specs = (
        ("fromNode", "fromNodeName", "upstream_endpoint"),
        ("toNode", "toNodeName", "downstream_endpoint"),
    )

    for id_key, name_key, role in endpoint_specs:
        endpoint_id = issue.get(id_key)
        if not endpoint_id:
            continue

        endpoint = _make_element(
            endpoint_id,
            name=issue.get(name_key),
            role=role,
            event=event,
            connected_link_ids=[source_id] if source_id else None,
        )
        related.append(endpoint)

    return primary, related


def _build_affected_elements(
    issues: list[dict[str, Any]],
    extra_links: list[dict[str, Any]] | None = None,
    extra_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    registry: dict[str, dict[str, dict[str, Any]]] = {
        "links": {},
        "nodes": {},
        "editorObjects": {},
    }

    formatted_issues: list[dict[str, Any]] = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        parsed = _parse_issue_id(issue.get("issueId", ""))
        event = _event_brief(issue, parsed)
        primary, related = _extract_issue_elements(issue, parsed, event)

        primary_id = primary.get("id", "")
        primary_category = primary.get("category", "unknown")
        bucket = {
            "link": "links",
            "node": "nodes",
            "editor_object": "editorObjects",
        }.get(primary_category)

        if bucket and primary_id:
            _registry_add(registry, bucket, primary_id, primary)

        for element in related:
            element_id = element.get("id", "")
            element_category = element.get("category", "unknown")
            element_bucket = {
                "link": "links",
                "node": "nodes",
                "editor_object": "editorObjects",
            }.get(element_category, "editorObjects")
            if element_id:
                _registry_add(registry, element_bucket, element_id, element)

        upstream = next((item for item in related if "upstream_endpoint" in item.get("roles", [])), None)
        downstream = next((item for item in related if "downstream_endpoint" in item.get("roles", [])), None)

        priority = _extract_priority(issue)
        formatted_issues.append(
            _drop_empty_values(
                {
                    "summary": _format_issue_summary(
                        issue,
                        parsed,
                        primary.get("name"),
                        primary.get("id"),
                    ),
                    **event,
                    "primaryElement": _drop_empty_values(
                        {
                            "category": primary_category,
                            "id": primary.get("id"),
                            "name": primary.get("name"),
                        }
                    ),
                    "topology": _build_topology_description(
                        upstream.get("name") if upstream else None,
                        primary.get("name"),
                        downstream.get("name") if downstream else None,
                    ),
                    "connectedElements": [
                        _drop_empty_values(
                            {
                                "category": element.get("category"),
                                "id": element.get("id"),
                                "name": element.get("name"),
                                "role": ROLE_LABELS.get(element["roles"][0], element["roles"][0])
                                if element.get("roles")
                                else None,
                                "roleCode": element["roles"][0] if element.get("roles") else None,
                            }
                        )
                        for element in related
                    ],
                    "metrics": _metric_fields(issue) or None,
                    "priority": priority,
                    "priorityScore": priority.get("priorityScore") if priority else None,
                    "priorityBand": priority.get("priorityBand") if priority else None,
                    "priorityReasons": priority.get("priorityReasons") if priority else None,
                }
            )
        )

    if extra_links:
        for link in extra_links:
            if not isinstance(link, dict):
                continue
            link_id = link.get("id") or link.get("sourceId")
            if not link_id:
                continue
            _registry_add(
                registry,
                "links",
                link_id,
                _make_element(
                    link_id,
                    name=link.get("displayName") or link.get("name"),
                    category="link",
                    metrics=_metric_fields(link) or None,
                ),
            )

    if extra_nodes:
        for node in extra_nodes:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id") or node.get("sourceId")
            if not node_id:
                continue
            _registry_add(
                registry,
                "nodes",
                node_id,
                _make_element(
                    node_id,
                    name=node.get("displayName") or node.get("name"),
                    category="node",
                    metrics=_metric_fields(node) or None,
                ),
            )

    affected = {
        "links": list(registry["links"].values()),
        "nodes": list(registry["nodes"].values()),
        "editorObjects": list(registry["editorObjects"].values()),
    }

    for bucket_name, elements in affected.items():
        for element in elements:
            element["roles"] = _unique_list(element.get("roles", []))
            element["rolesLabel"] = [ROLE_LABELS.get(role, role) for role in element["roles"]]

    return affected, formatted_issues


def _summarize_inventory(affected: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "linkCount": len(affected["links"]),
        "nodeCount": len(affected["nodes"]),
        "editorObjectCount": len(affected["editorObjects"]),
        "hasAffectedLinks": len(affected["links"]) > 0,
        "hasAffectedNodes": len(affected["nodes"]) > 0,
        "hasAffectedEditorObjects": len(affected["editorObjects"]) > 0,
    }


def _extract_context_section(raw: dict[str, Any], key: str) -> list[dict[str, Any]] | None:
    context = raw.get("context")
    if isinstance(context, dict) and isinstance(context.get(key), list):
        return context[key]
    if isinstance(raw.get(key), list):
        return raw[key]
    return None


ISSUE_LIST_KEYS = (
    "triggeredIssues",
    "triggered_issues",
    "issues",
    "riskEvents",
    "risk_events",
    "events",
)

ISSUE_ENRICHMENT_KEYS = (
    "eventId",
    "issueId",
    "eventType",
    "severity",
    "source",
    "sourceId",
    "displayName",
    "sourceEditorName",
    "fromNode",
    "fromNodeName",
    "toNode",
    "toNodeName",
    "flowCms",
    "depthRatio",
    "fullness",
    "blockageRatio",
    "direction",
    "rainfallRatio",
    "rainfallPercent",
    "maxRainfallMmPerHour",
    "capacityRatio",
    "velocityMps",
    "floodingCms",
    "metrics",
    "reason",
    "priorityScore",
    "priorityBand",
    "priorityReasons",
)


def _parse_json_object(swmm_raw_data: str) -> dict[str, Any]:
    cleaned = swmm_raw_data.strip()
    if not cleaned:
        raise ValueError("swmm_raw_data가 비어 있습니다.")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"swmm_raw_data JSON 파싱 실패: {exc}") from exc

    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError as exc:
            raise ValueError(f"swmm_raw_data 이중 JSON 파싱 실패: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("swmm_raw_data는 JSON 객체여야 합니다.")

    return parsed


def _parse_dispatch_key(dispatch_key: str | None) -> dict[str, Any] | None:
    if not dispatch_key:
        return None

    parts = dispatch_key.split(":")
    for index, part in enumerate(parts):
        if part not in EVENT_TYPE_LABELS:
            continue
        if index + 3 >= len(parts):
            continue

        category = parts[index + 1]
        element_id = parts[index + 2]
        severity = parts[index + 3]
        if category.lower() not in {"link", "pipe", "node", "junction", "editor_object", "connector"}:
            continue

        issue = {
            "issueId": f"{part}:{category}:{element_id}",
            "eventType": part,
            "severity": severity,
            "sourceId": element_id,
        }

        if index >= 2:
            issue["dispatchRunId"] = parts[0]
            issue["dispatchStepIndex"] = parts[1]

        return issue

    return None


def _looks_like_issue(value: dict[str, Any]) -> bool:
    return any(
        value.get(key)
        for key in ("issueId", "eventType", "sourceId", "severity")
    )


def _enrich_issue(issue: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(issue)
    sources = [raw]
    context = raw.get("context")
    if isinstance(context, dict):
        sources.append(context)

    for source in sources:
        for key in ISSUE_ENRICHMENT_KEYS:
            if key not in enriched and source.get(key) is not None:
                enriched[key] = source.get(key)

    return enriched


def _issue_dedupe_key(issue: dict[str, Any]) -> str:
    if issue.get("issueId"):
        return str(issue["issueId"])
    return "|".join(
        str(issue.get(key, ""))
        for key in ("eventType", "sourceId", "severity")
    )


def _extract_raw_issues(raw: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []

    for key in ISSUE_LIST_KEYS:
        value = raw.get(key)
        if isinstance(value, list):
            collected.extend(item for item in value if isinstance(item, dict))

    context = raw.get("context")
    if isinstance(context, dict):
        for key in ISSUE_LIST_KEYS:
            value = context.get(key)
            if isinstance(value, list):
                collected.extend(item for item in value if isinstance(item, dict))

    if _looks_like_issue(raw):
        collected.append(raw)

    dispatch_issue = _parse_dispatch_key(raw.get("dispatchKey"))
    if dispatch_issue:
        collected.append(dispatch_issue)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for issue in collected:
        enriched = _enrich_issue(issue, raw)
        dedupe_key = _issue_dedupe_key(enriched)
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(enriched)

    return deduped


def _merge_simulation_metadata(raw: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    nested_simulation = raw.get("simulation") if isinstance(raw.get("simulation"), dict) else {}
    simulation = _drop_empty_values(
        {
            "modelTime": raw.get("modelTime") or nested_simulation.get("modelTime"),
            "runId": raw.get("runId") or nested_simulation.get("runId"),
            "stepIndex": raw.get("stepIndex") or nested_simulation.get("stepIndex"),
            "forecastMinutes": nested_simulation.get("forecastMinutes"),
            "windowSeconds": nested_simulation.get("windowSeconds"),
            "control": nested_simulation.get("control"),
            "status": STATUS_LABELS.get(raw.get("status"), raw.get("status")),
            "statusCode": raw.get("status"),
            "reason": REASON_LABELS.get(raw.get("reason"), raw.get("reason")),
            "reasonCode": raw.get("reason"),
            "highestSeverity": SEVERITY_LABELS.get(
                raw.get("highestSeverity"), raw.get("highestSeverity")
            ),
            "highestSeverityCode": raw.get("highestSeverity"),
            "riskEventCount": raw.get("riskEventCount"),
            "contextLevel": raw.get("contextLevel"),
            "loggedAt": raw.get("loggedAt"),
            "schemaVersion": raw.get("schemaVersion"),
            "systemMeta": raw.get("systemMeta"),
        }
    )

    if issues:
        first_issue = issues[0]
        if simulation.get("runId") is None and first_issue.get("dispatchRunId") is not None:
            simulation["runId"] = first_issue.get("dispatchRunId")
        if simulation.get("stepIndex") is None and first_issue.get("dispatchStepIndex") is not None:
            simulation["stepIndex"] = first_issue.get("dispatchStepIndex")
        if simulation.get("highestSeverityCode") is None and first_issue.get("severity"):
            simulation["highestSeverityCode"] = first_issue.get("severity")
            simulation["highestSeverity"] = SEVERITY_LABELS.get(
                first_issue.get("severity"), first_issue.get("severity")
            )

    return simulation


def format_swmm_raw_data(swmm_raw_data: str) -> dict[str, Any]:
    raw = _parse_json_object(swmm_raw_data)
    issues = _extract_raw_issues(raw)

    if not issues:
        raise ValueError(
            "swmm_raw_data에서 이슈를 찾지 못했습니다. "
            f"수신 키: {sorted(raw.keys())}. "
            "triggeredIssues 또는 dispatchKey가 필요합니다."
        )

    extra_links = _extract_context_section(raw, "links")
    extra_nodes = _extract_context_section(raw, "nodes")

    affected_elements, formatted_issues = _build_affected_elements(
        issues,
        extra_links=extra_links,
        extra_nodes=extra_nodes,
    )

    return {
        "simulation": _merge_simulation_metadata(raw, issues),
        "affectedElements": affected_elements,
        "affectedElementsSummary": _summarize_inventory(affected_elements),
        "issues": formatted_issues,
        "priorityTargets": _build_priority_targets(formatted_issues),
    }


def _simplify_element_for_llm(element: dict[str, Any]) -> dict[str, Any]:
    events = element.get("relatedEvents", [])
    event_summary = None
    if events:
        event_summary = ", ".join(
            f"{event.get('event', '이벤트')}({event.get('severity', '미상')})"
            for event in events
            if isinstance(event, dict)
        )

    roles = element.get("rolesLabel") or element.get("roles") or []

    return _drop_empty_values(
        {
            "id": element.get("id"),
            "name": element.get("name"),
            "role": ", ".join(roles) if roles else None,
            "eventSummary": event_summary,
            "editorObjectType": element.get("editorObjectTypeLabel") or element.get("editorObjectType"),
            "connectedLinkIds": element.get("connectedLinkIds"),
            **(element.get("metrics") or {}),
        }
    )


def build_analysis_payload(scenario_id: str, weather_data: dict[str, Any], swmm_raw_data: str) -> dict[str, Any]:
    swmm_context = format_swmm_raw_data(swmm_raw_data)
    affected = swmm_context["affectedElements"]

    return {
        "scenarioId": scenario_id,
        "weatherObservation": weather_data,
        "link": [_simplify_element_for_llm(item) for item in affected["links"]],
        "node": [_simplify_element_for_llm(item) for item in affected["nodes"]],
        "editorObject": [_simplify_element_for_llm(item) for item in affected["editorObjects"]],
        "swmmSimulation": swmm_context["simulation"],
        "swmmIssues": swmm_context["issues"],
        "priorityTargets": swmm_context["priorityTargets"],
    }


def build_llm_message(analysis_input: dict[str, Any]) -> str:
    lines = [
        "아래 JSON을 분석하세요.",
        "",
        "[현장 우선순위 - 반드시 이 순서를 따를 것]",
    ]

    priority_targets = analysis_input.get("priorityTargets") or []
    if not priority_targets:
        lines.append("- 우선순위 산정 정보 없음")
    else:
        for target in priority_targets:
            reasons = ", ".join(target.get("priorityReasons") or [])
            lines.append(
                "- "
                f"{target.get('rank')}순위: {target.get('targetId')} / "
                f"{target.get('riskLabel')} / {target.get('priorityBand')} / "
                f"점수 {target.get('priorityScore')} / 근거: {reasons or '없음'}"
            )

    lines.extend(["", "[영향 시설 요약 - 응답 대상 항목에 반드시 사용]"])

    for label, key in (
        ("관로", "link"),
        ("맨홀/집수구/주변 지점", "node"),
    ):
        items = analysis_input.get(key, [])
        if not items:
            lines.append(f"- {label}: 없음")
            continue
        for item in items:
            name = item.get("name") or item.get("id") or "이름 없음"
            element_id = item.get("id", "id 없음")
            role = item.get("role")
            suffix = f" / {role}" if role else ""
            lines.append(f"- {label}: {name} ({element_id}){suffix}")

    past_history = analysis_input.get("past_history") or []
    lines.extend(["", "[과거 조치 이력]"])
    if not past_history:
        lines.append("- 없음")
    else:
        for record in past_history:
            lines.append(
                f"- {record.get('sourceId')}: {record.get('action_details')} "
                f"({record.get('loggedAt', '기록시각 없음')})"
            )

    lines.extend(["", "[분석 입력 JSON]", json.dumps(analysis_input, ensure_ascii=False, indent=2)])
    return "\n".join(lines)
