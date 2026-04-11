"""add issue position fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0005"
down_revision = "20260411_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("proofread_issues")}
    if "position_start" not in existing_columns:
        op.add_column("proofread_issues", sa.Column("position_start", sa.Integer(), nullable=True))
    if "position_end" not in existing_columns:
        op.add_column("proofread_issues", sa.Column("position_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("proofread_issues")}
    if "position_end" in existing_columns:
        op.drop_column("proofread_issues", "position_end")
    if "position_start" in existing_columns:
        op.drop_column("proofread_issues", "position_start")
