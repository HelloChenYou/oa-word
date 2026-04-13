"""add vector storage for knowledge chunks"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0007"
down_revision = "20260412_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_chunks")}

    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        if "embedding" not in columns:
            op.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(128)")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding "
            "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )
    elif "embedding" not in columns:
        op.add_column("knowledge_chunks", sa.Column("embedding", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_chunks")}

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
        if "embedding" in columns:
            op.execute("ALTER TABLE knowledge_chunks DROP COLUMN embedding")
    elif "embedding" in columns:
        op.drop_column("knowledge_chunks", "embedding")
