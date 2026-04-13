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


class RagHitOut(BaseModel):
    chunk_index: int
    document_id: str
    document_name: str
    knowledge_chunk_index: int
    score: float
    content_preview: str
    created_at: str


class TaskResultResp(BaseModel):
    task_id: str
    status: str
    summary: dict
    issues: List[IssueOut]
    rag_hits: List[RagHitOut] = []


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


class CreateKnowledgeResp(BaseModel):
    document_id: str
    name: str
    doc_type: str
    file_type: str
    chunk_count: int


class KnowledgeOut(BaseModel):
    document_id: str
    name: str
    doc_type: str
    file_type: str
    enabled: bool
    chunk_count: int
    created_at: str


class KnowledgeDetailResp(KnowledgeOut):
    raw_text: str


class UpdateKnowledgeReq(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    doc_type: str | None = Field(default=None, min_length=1, max_length=32)
    enabled: bool | None = None
    raw_text: str | None = Field(default=None, min_length=1)


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
    enabled: bool | None = None


class RuleOut(KnowledgeRule):
    owner_id: str | None = None


class LoginReq(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthUserOut(BaseModel):
    username: str
    role: str
    must_change_password: bool = False


class LoginResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserOut


class ChangePasswordReq(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class ChangePasswordResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserOut


class CreateUserReq(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    role: Literal["admin", "operator"] = "operator"
    enabled: bool = True
    must_change_password: bool = True


class UpdateUserReq(BaseModel):
    role: Literal["admin", "operator"] | None = None
    enabled: bool | None = None
    must_change_password: bool | None = None


class ResetUserPasswordReq(BaseModel):
    new_password: str = Field(min_length=8)
    must_change_password: bool = True


class UserOut(BaseModel):
    username: str
    role: str
    enabled: bool
    must_change_password: bool
    created_at: str
