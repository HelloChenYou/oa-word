"""add user accounts"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0003"
down_revision = "20260411_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_accounts" not in existing_tables:
        op.create_table(
            "user_accounts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_user_accounts_username"), "user_accounts", ["username"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "user_accounts" in existing_tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("user_accounts")}
        if op.f("ix_user_accounts_username") in existing_indexes:
            op.drop_index(op.f("ix_user_accounts_username"), table_name="user_accounts")
        op.drop_table("user_accounts")
