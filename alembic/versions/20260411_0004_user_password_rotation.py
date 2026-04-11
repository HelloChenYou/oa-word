"""add must change password flag"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0004"
down_revision = "20260411_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user_accounts")}
    if "must_change_password" not in existing_columns:
        op.add_column(
            "user_accounts",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.alter_column("user_accounts", "must_change_password", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user_accounts")}
    if "must_change_password" in existing_columns:
        op.drop_column("user_accounts", "must_change_password")
