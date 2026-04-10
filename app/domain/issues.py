from typing import Literal

from pydantic import BaseModel, ConfigDict


Severity = Literal["P0", "P1", "P2"]
Category = Literal["spelling", "grammar", "punctuation", "style", "terminology", "compliance", "structure", "logic"]
IssueSource = Literal["llm", "rule_engine"]


class BaseIssue(BaseModel):
    """Canonical issue payload shared across LLM, storage, and API layers."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity
    category: Category
    title: str
    original_text: str
    suggested_text: str
    reason: str
    evidence: str
    confidence: float
    source: IssueSource


class LlmIssue(BaseIssue):
    source: Literal["llm"]


class RuleIssue(BaseIssue):
    source: Literal["rule_engine"]


class StoredIssue(BaseIssue):
    pass


class LlmIssuesResp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[LlmIssue]
