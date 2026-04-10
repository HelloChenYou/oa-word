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
        title="测试规则",
        severity="P1",
        category=category,
        pattern=pattern,
        replacement=replacement,
        reason=reason,
        evidence=f"test:{rule_id}",
        enabled=True,
    )


def test_load_rules_includes_public_private_and_template_rules(monkeypatch):
    monkeypatch.setattr(rule_engine, "load_public_rules", lambda: [make_rule("public_a", "public", "term_replace", "terminology", "登陆", "登录", "公共")])
    monkeypatch.setattr(rule_engine, "load_private_rules", lambda owner_id: [make_rule("private_a", "private", "term_replace", "style", "截止时间", "截至时间", "私人")])
    monkeypatch.setattr(rule_engine, "build_template_rules", lambda template_rule_pack: [make_rule("template_a", "template", "required_section", "structure", "一、工作目标", "", "模板")])

    rules = rule_engine.load_rules(owner_id="demo_user", template_rule_pack='{"required_sections":["一、工作目标"]}')
    rule_ids = {rule.rule_id for rule in rules}
    assert rule_ids == {"public_a", "private_a", "template_a"}


def test_check_rules_applies_public_and_private_rules(monkeypatch):
    monkeypatch.setattr(rule_engine, "load_rules", lambda owner_id, template_rule_pack="{}": [
        make_rule("public_a", "public", "term_replace", "terminology", "登陆", "登录", "公共"),
        make_rule("private_a", "private", "term_replace", "style", "截止时间", "截至时间", "私人"),
    ])

    issues = rule_engine.check_rules("请各部门登陆OA系统，截止时间后不再受理。", owner_id="demo_user")
    categories = {issue.category for issue in issues}
    suggested_texts = {issue.suggested_text for issue in issues}
    assert "terminology" in categories
    assert "style" in categories
    assert "登录" in suggested_texts
    assert "截至时间" in suggested_texts


def test_check_rules_applies_template_required_section_rule(monkeypatch):
    monkeypatch.setattr(rule_engine, "load_rules", lambda owner_id, template_rule_pack="{}": [
        make_rule("template_a", "template", "required_section", "structure", "一、工作目标", "", "模板")
    ])

    issues = rule_engine.check_rules("这是一段没有章节标题的文本。", template_rule_pack='{"required_sections":["一、工作目标"]}')
    assert len(issues) == 1
    assert issues[0].category == "structure"
    assert issues[0].suggested_text == "一、工作目标"
