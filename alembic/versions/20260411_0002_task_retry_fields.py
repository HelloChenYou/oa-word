"""add task retry fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("proofread_tasks")}

    if "owner_id" not in existing_columns:
        op.add_column("proofread_tasks", sa.Column("owner_id", sa.String(length=64), nullable=True))
    if "failure_reason" not in existing_columns:
        op.add_column("proofread_tasks", sa.Column("failure_reason", sa.String(length=64), nullable=False, server_default=""))
        op.alter_column("proofread_tasks", "failure_reason", server_default=None)
    if "retry_count" not in existing_columns:
        op.add_column("proofread_tasks", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        op.alter_column("proofread_tasks", "retry_count", server_default=None)
    if "max_retries" not in existing_columns:
        op.add_column("proofread_tasks", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="0"))
        op.alter_column("proofread_tasks", "max_retries", server_default=None)
    if "last_error_at" not in existing_columns:
        op.add_column("proofread_tasks", sa.Column("last_error_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("proofread_tasks", "last_error_at")
    op.drop_column("proofread_tasks", "max_retries")
    op.drop_column("proofread_tasks", "retry_count")
    op.drop_column("proofread_tasks", "failure_reason")
    op.drop_column("proofread_tasks", "owner_id")
