from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.issues import Category, Severity


RuleScope = Literal["public", "private", "template"]
RuleKind = Literal["term_replace", "regex_mask", "required_section"]


class KnowledgeRule(BaseModel):
    """Configurable rule definition loaded from lightweight knowledge files."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    scope: RuleScope
    kind: RuleKind
    title: str
    severity: Severity
    category: Category
    pattern: str
    replacement: str = ""
    reason: str
    evidence: str
    enabled: bool = True
