"""Store nurse-collected background intake on the child record."""

from alembic import op
import sqlalchemy as sa

revision = "0007_registration_intake"
down_revision = "0006_doctor_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("children", sa.Column("registration_intake", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("children", "registration_intake")
