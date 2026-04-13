from app.domain.issues import StoredIssue
from app.services import orchestrator


def make_llm_issue(original_text: str, suggested_text: str = "replacement") -> StoredIssue:
    return StoredIssue(
        severity="P1",
        category="style",
        title="LLM issue",
        original_text=original_text,
        suggested_text=suggested_text,
        reason="reason",
        evidence="llm",
        confidence=0.9,
        source="llm",
    )


def test_fill_issue_positions_from_chunk_fills_missing_positions():
    issues = orchestrator._fill_issue_positions_from_chunk(
        [make_llm_issue("login")],
        chunk="please login now",
        offset=100,
    )

    assert issues[0].position_start == 107
    assert issues[0].position_end == 112


def test_fill_issue_positions_from_chunk_uses_next_match_for_repeated_text():
    issues = orchestrator._fill_issue_positions_from_chunk(
        [make_llm_issue("login", "sign in"), make_llm_issue("login", "log in")],
        chunk="login and login again",
        offset=10,
    )

    assert issues[0].position_start == 10
    assert issues[0].position_end == 15
    assert issues[1].position_start == 20
    assert issues[1].position_end == 25


def test_fill_issue_positions_from_chunk_converts_existing_chunk_positions_to_document_positions():
    issue = make_llm_issue("login")
    issue = issue.model_copy(update={"position_start": 7, "position_end": 12})

    issues = orchestrator._fill_issue_positions_from_chunk([issue], chunk="please login", offset=100)

    assert issues[0].position_start == 107
    assert issues[0].position_end == 112


def test_fill_issue_positions_from_chunk_falls_back_when_model_position_is_out_of_range():
    issue = make_llm_issue("login")
    issue = issue.model_copy(update={"position_start": 99, "position_end": 100})

    issues = orchestrator._fill_issue_positions_from_chunk([issue], chunk="please login", offset=100)

    assert issues[0].position_start == 107
    assert issues[0].position_end == 112


def test_fill_issue_positions_from_chunk_falls_back_when_model_position_points_to_wrong_text():
    issue = make_llm_issue("OA系统", "OA平台")
    issue = issue.model_copy(update={"position_start": 12, "position_end": 17})

    issues = orchestrator._fill_issue_positions_from_chunk(
        [issue],
        chunk="请各部门登录OA系统，并上报员工手机号13800138000。",
        offset=0,
    )

    assert issues[0].position_start == 6
    assert issues[0].position_end == 10


def test_run_proofread_fills_llm_positions(monkeypatch):
    monkeypatch.setattr(orchestrator, "_build_rule_pack", lambda owner_id, template_rule_pack="{}": "{}")
    monkeypatch.setattr(orchestrator, "check_rules", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestrator, "build_rag_context", lambda *args, **kwargs: "无")

    async def fake_check_with_llm(chunk, mode, scene, rule_pack="{}", rag_context="无"):
        return [make_llm_issue("login")]

    monkeypatch.setattr(orchestrator, "check_with_llm", fake_check_with_llm)

    issues = orchestrator.run_proofread_sync("please login now", mode="review", scene="general")

    assert len(issues) == 1
    assert issues[0].source == "llm"
    assert issues[0].position_start == 7
    assert issues[0].position_end == 12


def test_filter_overexpanded_llm_issues_drops_sentence_suggestion_for_local_text():
    issue = make_llm_issue(
        "民淆",
        "船夫哼着动听的民谣",
    )

    filtered = orchestrator._filter_overexpanded_llm_issues([issue], chunk="船夫哼着动听的民淆")

    assert filtered == []


def test_filter_overexpanded_llm_issues_keeps_minimal_suggestion():
    issue = make_llm_issue("民淆", "民谣")

    filtered = orchestrator._filter_overexpanded_llm_issues([issue], chunk="船夫哼着动听的民淆")

    assert filtered == [issue]
