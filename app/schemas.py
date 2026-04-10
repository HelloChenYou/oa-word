from typing import List, Literal

from pydantic import BaseModel, Field

from app.domain.issues import LlmIssuesResp, StoredIssue
from app.domain.rules import KnowledgeRule, RuleScope


Mode = Literal["review", "rewrite"]
Scene = Literal["general", "contract", "announcement", "tech_doc"]


class CreateTaskReq(BaseModel):
    mode: Mode = "review"
    scene: Scene = "general"
    text: str = Field(min_length=1)
    template_id: str | None = None
    owner_id: str | None = None


class CreateTaskResp(BaseModel):
    task_id: str
    status: str


class TaskStatusResp(BaseModel):
    task_id: str
    status: str


class IssueOut(StoredIssue):
    """External API issue shape."""


class TaskResultResp(BaseModel):
    task_id: str
    status: str
    summary: dict
    issues: List[IssueOut]


class CreateTemplateResp(BaseModel):
    template_id: str
    name: str
    doc_type: str
    file_type: str
    parsed: dict


class TemplateOut(BaseModel):
    template_id: str
    name: str
    doc_type: str
    file_type: str
    created_at: str


class TemplateDetailResp(BaseModel):
    template_id: str
    name: str
    doc_type: str
    file_type: str
    raw_text: str
    parsed: dict
    created_at: str


class CreateRuleReq(BaseModel):
    owner_id: str | None = None
    scope: RuleScope
    kind: str
    title: str
    severity: str
    category: str
    pattern: str
    replacement: str = ""
    reason: str
    evidence: str
    enabled: bool = True


class RuleOut(KnowledgeRule):
    owner_id: str | None = None
