"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "templates" not in existing_tables:
        op.create_table(
            "templates",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("doc_type", sa.String(length=32), nullable=False),
            sa.Column("file_type", sa.String(length=16), nullable=False),
            sa.Column("file_path", sa.String(length=512), nullable=False),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("parsed_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "knowledge_rules" not in existing_tables:
        op.create_table(
            "knowledge_rules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("rule_id", sa.String(length=128), nullable=False),
            sa.Column("scope", sa.String(length=16), nullable=False),
            sa.Column("owner_id", sa.String(length=64), nullable=True),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("severity", sa.String(length=4), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("pattern", sa.Text(), nullable=False),
            sa.Column("replacement", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("evidence", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("knowledge_rules")} if "knowledge_rules" in set(sa.inspect(bind).get_table_names()) else set()
    if op.f("ix_knowledge_rules_owner_id") not in existing_indexes:
        op.create_index(op.f("ix_knowledge_rules_owner_id"), "knowledge_rules", ["owner_id"], unique=False)
    if op.f("ix_knowledge_rules_rule_id") not in existing_indexes:
        op.create_index(op.f("ix_knowledge_rules_rule_id"), "knowledge_rules", ["rule_id"], unique=True)
    if op.f("ix_knowledge_rules_scope") not in existing_indexes:
        op.create_index(op.f("ix_knowledge_rules_scope"), "knowledge_rules", ["scope"], unique=False)

    if "proofread_tasks" not in existing_tables:
        op.create_table(
            "proofread_tasks",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("mode", sa.String(length=16), nullable=False),
            sa.Column("scene", sa.String(length=32), nullable=False),
            sa.Column("template_id", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("source_text", sa.Text(), nullable=False),
            sa.Column("model_name", sa.String(length=64), nullable=False),
            sa.Column("error_msg", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "proofread_issues" not in existing_tables:
        op.create_table(
            "proofread_issues",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("task_id", sa.String(length=64), nullable=False),
            sa.Column("severity", sa.String(length=4), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("original_text", sa.Text(), nullable=False),
            sa.Column("suggested_text", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("evidence", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=16), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["proofread_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("proofread_issues")
    op.drop_table("proofread_tasks")
    op.drop_index(op.f("ix_knowledge_rules_scope"), table_name="knowledge_rules")
    op.drop_index(op.f("ix_knowledge_rules_rule_id"), table_name="knowledge_rules")
    op.drop_index(op.f("ix_knowledge_rules_owner_id"), table_name="knowledge_rules")
    op.drop_table("knowledge_rules")
    op.drop_table("templates")
