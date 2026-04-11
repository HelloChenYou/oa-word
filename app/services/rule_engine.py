import re
from collections import defaultdict
from typing import Literal

from app.domain.issues import StoredIssue
from app.domain.rules import KnowledgeRule
from app.logging_utils import get_logger, log_warning
from app.services.issue_converter import validate_rule_issue
from app.services.rule_repository import build_template_rules, load_private_rules, load_public_rules

logger = get_logger(__name__)
RuleExecutionLayer = Literal["chunk", "document", "all"]
MAX_REGEX_PATTERN_LENGTH = 256
MAX_REGEX_MATCHES_PER_RULE = 100
UNSAFE_REGEX_PATTERNS = (
    re.compile(r"\([^)]*[+*][^)]*\)[+*]"),
    re.compile(r"\([^)]*\{[^)]*\}[^)]*\)[+*]"),
)


def load_rules(owner_id: str | None, template_rule_pack: str = "{}") -> list[KnowledgeRule]:
    """Load public, private, and template rules in priority order."""
    return load_public_rules() + load_private_rules(owner_id) + build_template_rules(template_rule_pack)


def check_rules(
    text: str,
    owner_id: str | None = None,
    template_rule_pack: str = "{}",
    layer: RuleExecutionLayer = "all",
    offset: int = 0,
) -> list[StoredIssue]:
    """Execute layered rules and return canonical issue models."""
    issues: list[StoredIssue] = []
    rules = _filter_conflicting_rules(load_rules(owner_id=owner_id, template_rule_pack=template_rule_pack))

    for rule in rules:
        if layer == "chunk" and rule.kind == "required_section":
            continue
        if layer == "document" and rule.kind != "required_section":
            continue
        if rule.kind == "term_replace":
            issues.extend(_run_term_replace_rule(text, rule, offset=offset))
        elif rule.kind == "regex_mask":
            issues.extend(_run_regex_mask_rule(text, rule, offset=offset))
        elif rule.kind == "required_section":
            issue = _run_required_section_rule(text, rule)
            if issue is not None:
                issues.append(issue)

    return issues


def _filter_conflicting_rules(rules: list[KnowledgeRule]) -> list[KnowledgeRule]:
    """Keep the highest-priority rule when active rules target the same matcher differently."""
    grouped: dict[tuple[str, str], list[KnowledgeRule]] = defaultdict(list)
    for rule in rules:
        grouped[(rule.kind, rule.pattern)].append(rule)

    result: list[KnowledgeRule] = []
    for key, candidates in grouped.items():
        if len(candidates) == 1:
            result.append(candidates[0])
            continue

        signatures = {(rule.replacement, rule.category, rule.reason) for rule in candidates}
        if len(signatures) == 1:
            result.extend(candidates)
            continue

        winner = candidates[-1]
        skipped = [rule.rule_id for rule in candidates[:-1]]
        log_warning(
            logger,
            "rule_conflict_detected",
            kind=key[0],
            pattern=key[1],
            winner_rule_id=winner.rule_id,
            skipped_rule_ids=skipped,
        )
        result.append(winner)
    return result


def validate_regex_pattern(pattern: str) -> re.Pattern:
    if len(pattern) > MAX_REGEX_PATTERN_LENGTH:
        raise ValueError(f"regex pattern too long: max {MAX_REGEX_PATTERN_LENGTH} characters")
    for unsafe_pattern in UNSAFE_REGEX_PATTERNS:
        if unsafe_pattern.search(pattern):
            raise ValueError("regex pattern is unsafe: nested quantifiers are not allowed")
    return re.compile(pattern)


def _run_term_replace_rule(text: str, rule: KnowledgeRule, offset: int = 0) -> list[StoredIssue]:
    issues: list[StoredIssue] = []
    for match in re.finditer(re.escape(rule.pattern), text):
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
                    "position_start": offset + match.start(),
                    "position_end": offset + match.end(),
                }
            )
        )
    return issues


def _run_regex_mask_rule(text: str, rule: KnowledgeRule, offset: int = 0) -> list[StoredIssue]:
    issues: list[StoredIssue] = []
    try:
        pattern = validate_regex_pattern(rule.pattern)
    except ValueError as exc:
        log_warning(logger, "unsafe_regex_rule_skipped", rule_id=rule.rule_id, error=str(exc))
        return []

    for index, match in enumerate(pattern.finditer(text), start=1):
        if index > MAX_REGEX_MATCHES_PER_RULE:
            log_warning(
                logger,
                "regex_match_limit_reached",
                rule_id=rule.rule_id,
                max_matches=MAX_REGEX_MATCHES_PER_RULE,
            )
            break
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
                    "position_start": offset + match.start(),
                    "position_end": offset + match.end(),
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
