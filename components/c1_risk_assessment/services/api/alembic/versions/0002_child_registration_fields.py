"""Add operational child registration fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_child_registration_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("children", sa.Column("full_name_encrypted", sa.String(length=512), nullable=True))
    op.add_column("children", sa.Column("district", sa.String(length=120), nullable=True))
    op.add_column("children", sa.Column("moh_area", sa.String(length=120), nullable=True))
    op.add_column("children", sa.Column("phm_area", sa.String(length=120), nullable=True))
    op.add_column("children", sa.Column("assigned_doctor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("children", sa.Column("external_patient_id_hash", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_children_assigned_doctor",
        "children",
        "users",
        ["assigned_doctor_id"],
        ["id"],
    )
    op.create_index("ix_children_facility_external_hash", "children", ["facility_id", "external_patient_id_hash"], unique=True)
    op.add_column("caregivers", sa.Column("reminder_consent", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("caregivers", "reminder_consent")
    op.drop_index("ix_children_facility_external_hash", table_name="children")
    op.drop_constraint("fk_children_assigned_doctor", "children", type_="foreignkey")
    op.drop_column("children", "external_patient_id_hash")
    op.drop_column("children", "assigned_doctor_id")
    op.drop_column("children", "phm_area")
    op.drop_column("children", "moh_area")
    op.drop_column("children", "district")
    op.drop_column("children", "full_name_encrypted")
