"""Structured clinician reviews + suggested follow-up status."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_clinician_reviews"
down_revision = "0002_child_registration_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FollowUpStatus uses str_enum (VARCHAR), not a Postgres ENUM — SUGGESTED needs no DDL.
    # If a native enum ever exists (older installs), extend it safely.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'follow_up_status') THEN
            ALTER TYPE follow_up_status ADD VALUE IF NOT EXISTS 'SUGGESTED';
          END IF;
        END $$;
        """
    )

    clinician_review_state = postgresql.ENUM(
        "PENDING", "COMPLETED", name="clinician_review_state", create_type=False
    )
    clinician_assessment = postgresql.ENUM(
        "AGREE", "DISAGREE", "FURTHER_ASSESSMENT_REQUIRED", name="clinician_assessment", create_type=False
    )
    clinician_workflow_action = postgresql.ENUM(
        "CONTINUE_MONITORING",
        "NUTRITION_REVIEW",
        "FURTHER_INVESTIGATION",
        "REFER",
        "REQUEST_INTERVENTION_REASSESSMENT",
        "NO_ACTION_RECORDED",
        name="clinician_workflow_action",
        create_type=False,
    )
    clinician_review_state.create(op.get_bind(), checkfirst=True)
    clinician_assessment.create(op.get_bind(), checkfirst=True)
    clinician_workflow_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clinician_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("review_state", clinician_review_state, nullable=False, server_default="PENDING"),
        sa.Column("clinician_assessment", clinician_assessment, nullable=True),
        sa.Column("clinician_status", sa.String(length=40), nullable=True),
        sa.Column("clinician_severity", sa.String(length=40), nullable=True),
        sa.Column("clinical_note", sa.Text(), nullable=True),
        sa.Column("workflow_action", clinician_workflow_action, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("prediction_id", name="uq_clinician_review_prediction"),
    )
    op.create_index("ix_clinician_reviews_facility_id", "clinician_reviews", ["facility_id"])
    op.create_index("ix_clinician_reviews_child_id", "clinician_reviews", ["child_id"])
    op.create_index("ix_clinician_reviews_visit_id", "clinician_reviews", ["visit_id"])
    op.create_index("ix_clinician_reviews_prediction_id", "clinician_reviews", ["prediction_id"])
    op.create_index("ix_clinician_reviews_review_state", "clinician_reviews", ["review_state"])


def downgrade() -> None:
    op.drop_index("ix_clinician_reviews_review_state", table_name="clinician_reviews")
    op.drop_index("ix_clinician_reviews_prediction_id", table_name="clinician_reviews")
    op.drop_index("ix_clinician_reviews_visit_id", table_name="clinician_reviews")
    op.drop_index("ix_clinician_reviews_child_id", table_name="clinician_reviews")
    op.drop_index("ix_clinician_reviews_facility_id", table_name="clinician_reviews")
    op.drop_table("clinician_reviews")
    op.execute("DROP TYPE IF EXISTS clinician_workflow_action")
    op.execute("DROP TYPE IF EXISTS clinician_assessment")
    op.execute("DROP TYPE IF EXISTS clinician_review_state")
