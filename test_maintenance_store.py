from maintenance_store import extract_source_ids


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
