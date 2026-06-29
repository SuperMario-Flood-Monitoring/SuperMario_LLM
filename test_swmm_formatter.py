import json

from swmm_formatter import build_analysis_payload, build_llm_message, format_swmm_raw_data

SAMPLE_SWMM_RAW = """
{
  "loggedAt": "2026-06-24T12:27:51.219",
  "dispatchKey": "20260624-122709-3bfc7bc5:333:REVERSE_FLOW:link:pipe_free_1781771885636:CRITICAL:333",
  "status": "scheduled",
  "runId": "20260624-122709-3bfc7bc5",
  "stepIndex": 333,
  "modelTime": "2026-06-16T00:05:33",
  "reason": "new_issue",
  "contextLevel": "optimal",
  "highestSeverity": "CRITICAL",
  "riskEventCount": 4,
  "contextSanitized": true,
  "triggeredIssues": [
    {
      "issueId": "REVERSE_FLOW:link:pipe_free_1781771885636",
      "eventType": "REVERSE_FLOW",
      "severity": "CRITICAL",
      "sourceId": "pipe_free_1781771885636",
      "displayName": "파이프",
      "sourceEditorName": "파이프",
      "fromNode": "teeConnector_copy_1781771853047_1",
      "fromNodeName": "T자 커넥터 102 복사 복사",
      "toNode": "CONN_COMB_01",
      "toNodeName": "합류식 커넥터 01"
    }
  ]
}
"""


def test_format_swmm_raw_data():
    formatted = format_swmm_raw_data(SAMPLE_SWMM_RAW)

    assert formatted["simulation"]["modelTime"] == "2026-06-16T00:05:33"
    assert formatted["simulation"]["highestSeverityCode"] == "CRITICAL"
    assert formatted["affectedElementsSummary"]["linkCount"] == 1
    assert formatted["affectedElementsSummary"]["editorObjectCount"] == 2
    assert formatted["affectedElementsSummary"]["nodeCount"] == 0

    link = formatted["affectedElements"]["links"][0]
    assert link["id"] == "pipe_free_1781771885636"
    assert link["name"] == "파이프"
    assert "issue_source" in link["roles"]

    editor_ids = {item["id"] for item in formatted["affectedElements"]["editorObjects"]}
    assert "teeConnector_copy_1781771853047_1" in editor_ids
    assert "CONN_COMB_01" in editor_ids

    issue = formatted["issues"][0]
    assert issue["eventCode"] == "REVERSE_FLOW"
    assert issue["primaryElement"]["category"] == "link"
    assert len(issue["connectedElements"]) == 2
    assert "->" in issue["topology"]
    assert "dispatchKey" not in json.dumps(formatted)


def test_build_analysis_payload():
    weather = {"RN-60m": 75.0, "TA": 18.5}
    payload = build_analysis_payload("폭우", weather, SAMPLE_SWMM_RAW)

    assert payload["scenarioId"] == "폭우"
    assert payload["weatherObservation"] == weather
    assert len(payload["link"]) == 1
    assert len(payload["editorObject"]) == 2
    assert payload["node"] == []
    assert payload["link"][0]["id"] == "pipe_free_1781771885636"
    assert payload["swmmIssues"][0]["eventCode"] == "REVERSE_FLOW"


def test_build_llm_message_contains_explicit_sections():
    payload = build_analysis_payload("폭우", {"RN-60m": 75.0}, SAMPLE_SWMM_RAW)
    message = build_llm_message(payload)

    assert '"link":' in message
    assert '"editorObject":' in message
    assert "pipe_free_1781771885636" in message
    assert "CONN_COMB_01" in message
    assert "- 관로:" in message
    assert "- 맨홀/집수구/주변 지점:" in message
    assert "- editor object:" not in message


def test_format_dispatch_key_only_payload():
    dispatch_only = """
    {
      "loggedAt": "2026-06-24T16:38:46.000",
      "dispatchKey": "20260624-163846-8d522cec:139:REVERSE_FLOW:link:pipe_free_1781772019999:CRITICAL:139",
      "status": "scheduled",
      "runId": "20260624-163846-8d522cec",
      "stepIndex": 139,
      "modelTime": "2026-06-16T00:05:33",
      "reason": "new_issue",
      "highestSeverity": "CRITICAL",
      "riskEventCount": 1
    }
    """
    payload = build_analysis_payload("폭우", {"RN-60m": 75.0}, dispatch_only)

    assert len(payload["link"]) == 1
    assert payload["link"][0]["id"] == "pipe_free_1781772019999"
    assert payload["swmmIssues"][0]["eventCode"] == "REVERSE_FLOW"


def test_build_analysis_payload_preserves_django_priority_targets():
    forecast_payload = {
        "schemaVersion": 1,
        "contextLevel": "forecast",
        "simulation": {
            "runId": "run-1",
            "stepIndex": 10,
            "modelTime": "2026-06-16T00:01:00",
            "forecastMinutes": 10,
            "windowSeconds": 120,
        },
        "highestSeverity": "CRITICAL",
        "riskEvents": [
            {
                "eventId": "PREDICTED_FULL_PIPE:link:PIPE_1",
                "eventType": "PREDICTED_FULL_PIPE",
                "severity": "CRITICAL",
                "source": "link",
                "sourceId": "PIPE_1",
                "metrics": {
                    "metric": "fullness",
                    "currentValue": 0.9,
                    "predictedValue": 0.99,
                    "forecastMinutes": 10,
                },
                "priorityScore": 92,
                "priorityBand": "P1",
                "priorityReasons": ["CRITICAL 위험", "만관 위험", "예측 증가량 0.09"],
            },
            {
                "eventId": "PREDICTED_NODE_DEPTH:node:NODE_1",
                "eventType": "PREDICTED_NODE_DEPTH",
                "severity": "CRITICAL",
                "source": "node",
                "sourceId": "NODE_1",
                "metrics": {
                    "metric": "depthRatio",
                    "currentValue": 0.7,
                    "predictedValue": 0.91,
                    "forecastMinutes": 10,
                },
                "priorityScore": 88,
                "priorityBand": "P1",
                "priorityReasons": ["CRITICAL 위험", "node 수위 위험"],
            },
        ],
    }

    payload = build_analysis_payload("폭우", {"RN-60m": 75.0}, json.dumps(forecast_payload))

    assert payload["swmmSimulation"]["runId"] == "run-1"
    assert payload["swmmSimulation"]["forecastMinutes"] == 10
    assert payload["link"][0]["id"] == "PIPE_1"
    assert payload["node"][0]["id"] == "NODE_1"
    assert payload["swmmIssues"][0]["priorityBand"] == "P1"
    assert payload["priorityTargets"][0]["targetId"] == "PIPE_1"
    assert payload["priorityTargets"][0]["priorityScore"] == 92
    assert payload["priorityTargets"][0]["prioritySource"] == "django"
    assert payload["priorityTargets"][1]["targetId"] == "NODE_1"


def test_build_analysis_payload_creates_fallback_priority_when_missing():
    forecast_payload = {
        "highestSeverity": "CRITICAL",
        "riskEvents": [
            {
                "eventId": "PREDICTED_CAPACITY_EXCEEDED:link:PIPE_9",
                "eventType": "PREDICTED_CAPACITY_EXCEEDED",
                "severity": "CRITICAL",
                "source": "link",
                "sourceId": "PIPE_9",
                "metrics": {"capacityRatio": 1.2},
            }
        ],
    }

    payload = build_analysis_payload("폭우", {"RN-60m": 75.0}, json.dumps(forecast_payload))

    priority = payload["priorityTargets"][0]
    assert priority["targetId"] == "PIPE_9"
    assert priority["prioritySource"] == "fallback"
    assert priority["priorityBand"] in {"P1", "P2"}
    assert "관로 용량 초과 위험" in priority["priorityReasons"]

