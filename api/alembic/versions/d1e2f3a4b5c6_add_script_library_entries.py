"""add script library entries

Revision ID: d1e2f3a4b5c6
Revises: c9d8e7f6a5b4
Create Date: 2026-07-29 01:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "script_library_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("definition_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "approval_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["definition_id"], ["workflow_definitions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_library_org", "script_library_entries", ["organization_id"])
    op.create_index(
        "ix_script_library_workflow", "script_library_entries", ["workflow_id"]
    )
    op.create_index(
        "ix_script_library_status", "script_library_entries", ["approval_status"]
    )
    op.create_index("ix_script_library_owner", "script_library_entries", ["owner_user_id"])
    op.create_index(
        op.f("ix_script_library_entries_id"), "script_library_entries", ["id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_script_library_entries_id"), table_name="script_library_entries")
    op.drop_index("ix_script_library_owner", table_name="script_library_entries")
    op.drop_index("ix_script_library_status", table_name="script_library_entries")
    op.drop_index("ix_script_library_workflow", table_name="script_library_entries")
    op.drop_index("ix_script_library_org", table_name="script_library_entries")
    op.drop_table("script_library_entries")
