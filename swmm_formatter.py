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
    if "pipe" in lowered or lowered.startswith("pipe"):
        return "link"
    if any(token in element_id for token in ("teeconnector", "connector", "conn_")):
        return "editor_object"
    if any(token in lowered for token in ("junction", "outfall", "divider", "storage")):
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
    metrics = _drop_empty_values(
        {
            "flowCms": source.get("flowCms"),
            "depthRatio": source.get("depthRatio"),
            "fullness": source.get("fullness"),
            "blockageRatio": source.get("blockageRatio"),
            "direction": source.get("direction"),
            "rainfallRatio": source.get("rainfallRatio"),
            "rainfallPercent": source.get("rainfallPercent"),
            "maxRainfallMmPerHour": source.get("maxRainfallMmPerHour"),
            "flooded": source.get("flooded"),
            "pondingDepth": source.get("pondingDepth"),
            "invertElevation": source.get("invertElevation"),
        }
    )

    if metrics.get("flowCms") is not None and metrics["flowCms"] < 0:
        metrics["flowDirectionNote"] = "음수 유량 - 역류 가능"
    elif metrics.get("direction") == "reverse":
        metrics["flowDirectionNote"] = "역류 방향"

    return metrics


def _event_brief(issue: dict[str, Any], parsed: dict[str, str | None]) -> dict[str, Any]:
    event_type = issue.get("eventType") or parsed.get("eventType")
    return _drop_empty_values(
        {
            "event": EVENT_TYPE_LABELS.get(event_type, event_type),
            "eventCode": event_type,
            "severity": SEVERITY_LABELS.get(issue.get("severity"), issue.get("severity")),
            "severityCode": issue.get("severity"),
            "issueId": issue.get("issueId"),
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


def _extract_issue_elements(
    issue: dict[str, Any],
    parsed: dict[str, str | None],
    event: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_id = issue.get("sourceId") or parsed.get("elementId") or ""
    source_name = issue.get("displayName") or issue.get("sourceEditorName")
    source_category = _classify_element(source_id, parsed.get("elementCategory"))
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
    "issueId",
    "eventType",
    "severity",
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
    simulation = _drop_empty_values(
        {
            "modelTime": raw.get("modelTime"),
            "runId": raw.get("runId"),
            "stepIndex": raw.get("stepIndex"),
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
    }


def build_llm_message(analysis_input: dict[str, Any]) -> str:
    lines = [
        "아래 JSON을 분석하세요.",
        "",
        "[영향 시설 요약 - 응답 3번 항목에 반드시 사용]",
    ]

    for label, key in (
        ("link", "link"),
        ("node", "node"),
        ("editor object", "editorObject"),
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
    lines.extend(["", "[과거 조치 이력 - past_history]"])
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
