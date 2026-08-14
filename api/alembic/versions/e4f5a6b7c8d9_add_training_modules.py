"""add training modules and attempts

Revision ID: e4f5a6b7c8d9
Revises: d1e2f3a4b5c6
Create Date: 2026-07-29 02:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "mode",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'shadow'"),
        ),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("script_entry_id", sa.Integer(), nullable=True),
        sa.Column(
            "success_codes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "difficulty",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'beginner'"),
        ),
        sa.Column("pass_score", sa.Float(), nullable=False, server_default="70"),
        sa.Column(
            "content", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["script_entry_id"],
            ["script_library_entries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["workflows.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_modules_org", "training_modules", ["organization_id"])
    op.create_index("ix_training_modules_mode", "training_modules", ["mode"])
    op.create_index(
        "ix_training_modules_published", "training_modules", ["is_published"]
    )
    op.create_index(op.f("ix_training_modules_id"), "training_modules", ["id"])

    op.create_table(
        "training_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "passed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "result", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("workflow_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["module_id"], ["training_modules.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_training_attempts_org", "training_attempts", ["organization_id"]
    )
    op.create_index(
        "ix_training_attempts_module", "training_attempts", ["module_id"]
    )
    op.create_index("ix_training_attempts_user", "training_attempts", ["user_id"])
    op.create_index(
        "ix_training_attempts_user_module",
        "training_attempts",
        ["user_id", "module_id"],
    )
    op.create_index(op.f("ix_training_attempts_id"), "training_attempts", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_training_attempts_id"), table_name="training_attempts")
    op.drop_index("ix_training_attempts_user_module", table_name="training_attempts")
    op.drop_index("ix_training_attempts_user", table_name="training_attempts")
    op.drop_index("ix_training_attempts_module", table_name="training_attempts")
    op.drop_index("ix_training_attempts_org", table_name="training_attempts")
    op.drop_table("training_attempts")

    op.drop_index(op.f("ix_training_modules_id"), table_name="training_modules")
    op.drop_index("ix_training_modules_published", table_name="training_modules")
    op.drop_index("ix_training_modules_mode", table_name="training_modules")
    op.drop_index("ix_training_modules_org", table_name="training_modules")
    op.drop_table("training_modules")
