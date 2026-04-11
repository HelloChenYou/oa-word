from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    position_start: int | None = Field(default=None, ge=0)
    position_end: int | None = Field(default=None, ge=0)


class LlmIssue(BaseIssue):
    source: Literal["llm"]
    position_start: int | None = Field(..., ge=0)
    position_end: int | None = Field(..., ge=0)


class RuleIssue(BaseIssue):
    source: Literal["rule_engine"]


class StoredIssue(BaseIssue):
    pass


class LlmIssuesResp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[LlmIssue]
