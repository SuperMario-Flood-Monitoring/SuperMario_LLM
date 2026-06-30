from maintenance_store import extract_source_ids, format_maintenance_case


def test_extract_source_ids_from_link_and_issue():
    analysis_input = {
        "link": [{"id": "pipe_free_123", "name": "파이프"}],
        "swmmIssues": [
            {
                "primaryElement": {"id": "pipe_free_123", "category": "link"},
            }
        ],
    }

    assert extract_source_ids(analysis_input) == ["pipe_free_123"]


def test_extract_source_ids_empty():
    assert extract_source_ids({}) == []


def test_format_maintenance_case_from_django_payload():
    payload = {
        "event": {
            "id": 1,
            "run_id": "20260624-164620-7faf56be",
            "step_index": 3087,
            "model_time": "2026-06-16T00:51:27",
            "target_id": "PIPE_1",
            "source": "link",
            "hazard_type": "REVERSE_FLOW",
            "hazard_level": "CRITICAL",
            "hazard_detail": "파이프 PIPE_1에서 역류가 감지되었습니다.",
            "priority": {
                "priorityScore": 92,
                "priorityBand": "P1",
                "priorityReasons": ["CRITICAL 위험", "만관 위험"],
            },
            "created_at": "2026-06-26T15:51:00",
        },
        "metrics": {
            "flowCms": -0.034,
            "direction": "reverse",
            "fullness": 0.92,
            "capacityRatio": 1.2,
            "blockageRatio": 0.4,
        },
        "action": {
            "status": "RESOLVED",
            "initial_action_detail": "하류 관로 현장 점검 완료",
            "action_type": "FIELD_CHECK",
            "result_detail": "토사 제거 후 수위 안정화",
            "result_status": "RESOLVED",
            "recurrence_note": "폭우 시 상류 맨홀 우선 점검",
            "created_at": "2026-06-26T15:52:00",
        },
    }

    formatted = format_maintenance_case(payload)

    assert "[도시침수 위험 대응 사례]" in formatted
    assert "시설 ID: PIPE_1" in formatted
    assert "위험 유형: REVERSE_FLOW" in formatted
    assert "현장 조치 우선순위:" in formatted
    assert "- 등급: P1" in formatted
    assert "- 점수: 92" in formatted
    assert "- 유량: -0.034 m3/s" in formatted
    assert "- 만관율: 92.0%" in formatted
    assert "- 초기 조치: 하류 관로 현장 점검 완료" in formatted
    assert "폭우 시 상류 맨홀 우선 점검" in formatted


def test_format_maintenance_case_requires_target_id():
    try:
        format_maintenance_case(
            {
                "event": {"id": 1},
                "metrics": {},
                "action": {"initial_action_detail": "점검 완료"},
            }
        )
    except ValueError as exc:
        assert "event.target_id" in str(exc)
    else:
        raise AssertionError("event.target_id 누락 시 ValueError가 발생해야 합니다.")
