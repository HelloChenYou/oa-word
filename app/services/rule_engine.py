import re

from app.domain.issues import StoredIssue
from app.domain.rules import KnowledgeRule
from app.services.issue_converter import validate_rule_issue
from app.services.rule_repository import build_template_rules, load_private_rules, load_public_rules


def load_rules(owner_id: str | None, template_rule_pack: str = "{}") -> list[KnowledgeRule]:
    """Load public, private, and template rules in priority order."""
    return load_public_rules() + load_private_rules(owner_id) + build_template_rules(template_rule_pack)


def check_rules(text: str, owner_id: str | None = None, template_rule_pack: str = "{}") -> list[StoredIssue]:
    """Execute layered rules and return canonical issue models."""
    issues: list[StoredIssue] = []
    rules = load_rules(owner_id=owner_id, template_rule_pack=template_rule_pack)

    for rule in rules:
        if rule.kind == "term_replace":
            issues.extend(_run_term_replace_rule(text, rule))
        elif rule.kind == "regex_mask":
            issues.extend(_run_regex_mask_rule(text, rule))
        elif rule.kind == "required_section":
            issue = _run_required_section_rule(text, rule)
            if issue is not None:
                issues.append(issue)

    return issues


def _run_term_replace_rule(text: str, rule: KnowledgeRule) -> list[StoredIssue]:
    issues: list[StoredIssue] = []
    for _ in re.finditer(re.escape(rule.pattern), text):
        issues.append(
            validate_rule_issue(
                {
                    "severity": rule.severity,
                    "category": rule.category,
                    "title": rule.title,
                    "original_text": rule.pattern,
                    "suggested_text": rule.replacement,
                    "reason": rule.reason,
                    "evidence": rule.evidence,
                    "confidence": 0.98,
                    "source": "rule_engine",
                }
            )
        )
    return issues


def _run_regex_mask_rule(text: str, rule: KnowledgeRule) -> list[StoredIssue]:
    issues: list[StoredIssue] = []
    for match in re.finditer(rule.pattern, text):
        hit = match.group(0)
        issues.append(
            validate_rule_issue(
                {
                    "severity": rule.severity,
                    "category": rule.category,
                    "title": rule.title,
                    "original_text": hit,
                    "suggested_text": f"{hit[:3]}****{hit[-4:]}",
                    "reason": rule.reason,
                    "evidence": rule.evidence,
                    "confidence": 0.99,
                    "source": "rule_engine",
                }
            )
        )
    return issues


def _run_required_section_rule(text: str, rule: KnowledgeRule) -> StoredIssue | None:
    if rule.pattern in text:
        return None
    return validate_rule_issue(
        {
            "severity": rule.severity,
            "category": rule.category,
            "title": rule.title,
            "original_text": "",
            "suggested_text": rule.pattern,
            "reason": rule.reason,
            "evidence": rule.evidence,
            "confidence": 0.95,
            "source": "rule_engine",
        }
    )
