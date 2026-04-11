from app.domain.rules import KnowledgeRule
from app.services import rule_engine


def make_rule(
    rule_id: str,
    scope: str,
    kind: str,
    category: str,
    pattern: str,
    replacement: str,
    reason: str,
) -> KnowledgeRule:
    return KnowledgeRule(
        rule_id=rule_id,
        scope=scope,
        kind=kind,
        title="Test rule",
        severity="P1",
        category=category,
        pattern=pattern,
        replacement=replacement,
        reason=reason,
        evidence=f"test:{rule_id}",
        enabled=True,
    )


def test_load_rules_includes_public_private_and_template_rules(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_public_rules",
        lambda: [make_rule("public_a", "public", "term_replace", "terminology", "login", "sign in", "public")],
    )
    monkeypatch.setattr(
        rule_engine,
        "load_private_rules",
        lambda owner_id: [make_rule("private_a", "private", "term_replace", "style", "deadline", "due date", "private")],
    )
    monkeypatch.setattr(
        rule_engine,
        "build_template_rules",
        lambda template_rule_pack: [
            make_rule("template_a", "template", "required_section", "structure", "Required section", "", "template")
        ],
    )

    rules = rule_engine.load_rules(owner_id="demo_user", template_rule_pack='{"required_sections":["Required section"]}')
    rule_ids = {rule.rule_id for rule in rules}
    assert rule_ids == {"public_a", "private_a", "template_a"}


def test_check_rules_applies_public_and_private_rules(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("public_a", "public", "term_replace", "terminology", "login", "sign in", "public"),
            make_rule("private_a", "private", "term_replace", "style", "deadline", "due date", "private"),
        ],
    )

    issues = rule_engine.check_rules("please login before deadline", owner_id="demo_user")
    suggested_texts = {issue.suggested_text for issue in issues}
    assert "sign in" in suggested_texts
    assert "due date" in suggested_texts


def test_check_rules_applies_template_required_section_rule(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("template_a", "template", "required_section", "structure", "Required section", "", "template")
        ],
    )

    issues = rule_engine.check_rules("body without heading", template_rule_pack='{"required_sections":["Required section"]}')
    assert len(issues) == 1
    assert issues[0].category == "structure"
    assert issues[0].suggested_text == "Required section"


def test_term_replace_rule_records_match_position(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("login", "public", "term_replace", "terminology", "login", "sign in", "term")
        ],
    )

    issues = rule_engine.check_rules("please login now", layer="chunk", offset=7)

    assert len(issues) == 1
    assert issues[0].position_start == 14
    assert issues[0].position_end == 19


def test_required_section_runs_only_on_document_layer(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("section", "template", "required_section", "structure", "Required", "", "template")
        ],
    )

    assert rule_engine.check_rules("body", layer="chunk") == []
    assert len(rule_engine.check_rules("body", layer="document")) == 1


def test_conflicting_rules_keep_highest_priority(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("public_login", "public", "term_replace", "terminology", "login", "log in", "public"),
            make_rule("private_login", "private", "term_replace", "terminology", "login", "sign in", "private"),
        ],
    )

    issues = rule_engine.check_rules("login", owner_id="demo_user")

    assert len(issues) == 1
    assert issues[0].suggested_text == "sign in"
    assert issues[0].evidence == "test:private_login"


def test_unsafe_regex_rule_is_skipped(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("unsafe", "public", "regex_mask", "compliance", "(a+)+$", "", "unsafe")
        ],
    )

    assert rule_engine.check_rules("aaaaaaaaaaaaaaaaab", layer="chunk") == []


def test_regex_rule_records_position_and_limits_matches(monkeypatch):
    monkeypatch.setattr(rule_engine, "MAX_REGEX_MATCHES_PER_RULE", 2)
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("phone", "public", "regex_mask", "compliance", r"1[3-9]\d{9}", "", "mask")
        ],
    )

    issues = rule_engine.check_rules("a 13800138000 b 13900139000 c 13700137000", layer="chunk", offset=10)

    assert len(issues) == 2
    assert issues[0].position_start == 12
    assert issues[0].position_end == 23


def test_mobile_regex_matches_phone_next_to_chinese_text(monkeypatch):
    monkeypatch.setattr(
        rule_engine,
        "load_rules",
        lambda owner_id, template_rule_pack="{}": [
            make_rule("phone", "public", "regex_mask", "compliance", r"(?<!\d)1[3-9]\d{9}(?!\d)", "", "mask")
        ],
    )

    issues = rule_engine.check_rules("员工手机号13800138000。", layer="chunk")

    assert len(issues) == 1
    assert issues[0].original_text == "13800138000"
    assert issues[0].suggested_text == "138****8000"
