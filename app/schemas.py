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
    retry_count: int = 0
    max_retries: int = 0
    failure_reason: str = ""
    error_msg: str = ""


class RetryTaskResp(BaseModel):
    task_id: str
    status: str
    retry_count: int
    max_retries: int


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


class UpdateRuleReq(BaseModel):
    scope: RuleScope | None = None
    kind: str | None = None
    title: str | None = None
    severity: str | None = None
    category: str | None = None
    pattern: str | None = None
    replacement: str | None = None
    reason: str | None = None
    evidence: str | None = None
    enabled: bool | None = None


class RuleOut(KnowledgeRule):
    owner_id: str | None = None
