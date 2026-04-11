"""add task retry fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proofread_tasks", sa.Column("owner_id", sa.String(length=64), nullable=True))
    op.add_column("proofread_tasks", sa.Column("failure_reason", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("proofread_tasks", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("proofread_tasks", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("proofread_tasks", sa.Column("last_error_at", sa.DateTime(), nullable=True))

    op.alter_column("proofread_tasks", "failure_reason", server_default=None)
    op.alter_column("proofread_tasks", "retry_count", server_default=None)
    op.alter_column("proofread_tasks", "max_retries", server_default=None)


def downgrade() -> None:
    op.drop_column("proofread_tasks", "last_error_at")
    op.drop_column("proofread_tasks", "max_retries")
    op.drop_column("proofread_tasks", "retry_count")
    op.drop_column("proofread_tasks", "failure_reason")
    op.drop_column("proofread_tasks", "owner_id")
