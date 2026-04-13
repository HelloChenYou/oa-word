"""add proofread rag hits

Revision ID: 20260413_0008
Revises: 20260413_0007
Create Date: 2026-04-13 00:08:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0008"
down_revision = "20260413_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proofread_rag_hits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("document_name", sa.String(length=128), nullable=False),
        sa.Column("knowledge_chunk_index", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["proofread_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proofread_rag_hits_task_id", "proofread_rag_hits", ["task_id"])
    op.create_index("ix_proofread_rag_hits_document_id", "proofread_rag_hits", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_proofread_rag_hits_document_id", table_name="proofread_rag_hits")
    op.drop_index("ix_proofread_rag_hits_task_id", table_name="proofread_rag_hits")
    op.drop_table("proofread_rag_hits")
