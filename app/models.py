from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProofreadTask(Base):
    __tablename__ = "proofread_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))
    scene: Mapped[str] = mapped_column(String(32))
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    source_text: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(64), default="")
    error_msg: Mapped[str] = mapped_column(Text, default="")
    failure_reason: Mapped[str] = mapped_column(String(64), default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProofreadIssue(Base):
    __tablename__ = "proofread_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("proofread_tasks.id"))
    severity: Mapped[str] = mapped_column(String(4))
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    original_text: Mapped[str] = mapped_column(Text)
    suggested_text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16))


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    doc_type: Mapped[str] = mapped_column(String(32), default="general")
    file_type: Mapped[str] = mapped_column(String(16))
    file_path: Mapped[str] = mapped_column(String(512))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeRuleRecord(Base):
    __tablename__ = "knowledge_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(16), index=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(4))
    category: Mapped[str] = mapped_column(String(32))
    pattern: Mapped[str] = mapped_column(Text)
    replacement: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
