"""add stepsales sales tables

Revision ID: c9d8e7f6a5b4
Revises: cdcf9f65913b
Create Date: 2026-07-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "cdcf9f65913b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stepsales_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("active_hiring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("roles_hiring_for", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("urgency", sa.String(length=32), nullable=True),
        sa.Column("timeline", sa.String(length=255), nullable=True),
        sa.Column("budget_signal", sa.String(length=100), nullable=True),
        sa.Column("interest_level", sa.String(length=32), nullable=True),
        sa.Column("next_step", sa.String(length=200), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="new"),
        sa.Column("extra", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )
    op.create_index("ix_stepsales_leads_id", "stepsales_leads", ["id"])
    op.create_index("ix_stepsales_leads_lead_id", "stepsales_leads", ["lead_id"], unique=True)
    op.create_index("ix_stepsales_leads_organization_id", "stepsales_leads", ["organization_id"])
    op.create_index("ix_stepsales_leads_status", "stepsales_leads", ["status"])
    op.create_index("ix_stepsales_leads_email", "stepsales_leads", ["email"])

    op.create_table(
        "stepsales_call_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=True),
        sa.Column("call_id", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("interest_level", sa.String(length=32), nullable=True),
        sa.Column("objection_type", sa.String(length=200), nullable=True),
        sa.Column("next_step", sa.String(length=200), nullable=True),
        sa.Column("callback_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outcome_id"),
    )
    op.create_index("ix_stepsales_call_outcomes_id", "stepsales_call_outcomes", ["id"])
    op.create_index(
        "ix_stepsales_call_outcomes_outcome_id",
        "stepsales_call_outcomes",
        ["outcome_id"],
        unique=True,
    )
    op.create_index("ix_stepsales_call_outcomes_org", "stepsales_call_outcomes", ["organization_id"])
    op.create_index("ix_stepsales_call_outcomes_lead", "stepsales_call_outcomes", ["lead_id"])

    op.create_table(
        "stepsales_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("list_price", sa.Float(), nullable=False),
        sa.Column("discount_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_reason", sa.String(length=500), nullable=True),
        sa.Column("final_price", sa.Float(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="proposal_pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id"),
    )
    op.create_index("ix_stepsales_offers_id", "stepsales_offers", ["id"])
    op.create_index("ix_stepsales_offers_offer_id", "stepsales_offers", ["offer_id"], unique=True)
    op.create_index("ix_stepsales_offers_org", "stepsales_offers", ["organization_id"])
    op.create_index("ix_stepsales_offers_lead", "stepsales_offers", ["lead_id"])

    op.create_table(
        "stepsales_followups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("followup_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("followup_type", sa.String(length=64), nullable=False),
        sa.Column("template_id", sa.String(length=128), nullable=False, server_default="default_v1"),
        sa.Column("next_step", sa.String(length=200), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("followup_id"),
    )
    op.create_index("ix_stepsales_followups_id", "stepsales_followups", ["id"])
    op.create_index(
        "ix_stepsales_followups_followup_id", "stepsales_followups", ["followup_id"], unique=True
    )
    op.create_index("ix_stepsales_followups_org", "stepsales_followups", ["organization_id"])

    op.create_table(
        "stepsales_appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("preferred_date", sa.String(length=32), nullable=False),
        sa.Column("preferred_time", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Berlin"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            server_default="second_call_scheduled",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index("ix_stepsales_appointments_id", "stepsales_appointments", ["id"])
    op.create_index(
        "ix_stepsales_appointments_appointment_id",
        "stepsales_appointments",
        ["appointment_id"],
        unique=True,
    )
    op.create_index("ix_stepsales_appointments_org", "stepsales_appointments", ["organization_id"])

    op.create_table(
        "stepsales_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_reference", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("offer_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("allowed_methods", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("payment_method", sa.String(length=64), nullable=True),
        sa.Column("payment_link", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("post_sale_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index("ix_stepsales_payments_id", "stepsales_payments", ["id"])
    op.create_index(
        "ix_stepsales_payments_payment_reference",
        "stepsales_payments",
        ["payment_reference"],
        unique=True,
    )
    op.create_index("ix_stepsales_payments_org", "stepsales_payments", ["organization_id"])

    op.create_table(
        "stepsales_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stepsales_events_id", "stepsales_events", ["id"])
    op.create_index("ix_stepsales_events_org", "stepsales_events", ["organization_id"])
    op.create_index("ix_stepsales_events_type", "stepsales_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("stepsales_events")
    op.drop_table("stepsales_payments")
    op.drop_table("stepsales_appointments")
    op.drop_table("stepsales_followups")
    op.drop_table("stepsales_offers")
    op.drop_table("stepsales_call_outcomes")
    op.drop_table("stepsales_leads")
