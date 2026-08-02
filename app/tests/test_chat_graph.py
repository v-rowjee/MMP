from app.graph.chat import build_chat_graph


def test_chat_graph_runs_full_skeleton_flow():
    result = build_chat_graph().invoke(
        {
            "analysis_id": "analysis_123",
            "dataset_id": "dataset_123",
            "session_id": "session_123",
            "question": "What are the main trends?",
        }
    )

    assert result["history"] == []
    assert result["schema"] == {}
    assert result["dashboard_context"] == {}
    assert result["route"] == "dashboard"
    assert result["query_plan"] is None
    assert result["sql"] is None
    assert result["query_result"] == []
    assert result["answer"] == ""
    assert result["errors"] == []
