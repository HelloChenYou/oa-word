"""add lightweight knowledge base tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260412_0006"
down_revision = "20260411_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "knowledge_documents" not in existing_tables:
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("doc_type", sa.String(length=32), nullable=False),
            sa.Column("file_type", sa.String(length=16), nullable=False),
            sa.Column("file_path", sa.String(length=512), nullable=False),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "knowledge_chunks" not in existing_tables:
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("document_id", sa.String(length=64), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "knowledge_chunks" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("knowledge_chunks")}
        if op.f("ix_knowledge_chunks_document_id") in existing_indexes:
            op.drop_index(op.f("ix_knowledge_chunks_document_id"), table_name="knowledge_chunks")
        op.drop_table("knowledge_chunks")
    if "knowledge_documents" in existing_tables:
        op.drop_table("knowledge_documents")
