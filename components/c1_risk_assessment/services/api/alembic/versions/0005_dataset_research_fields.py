"""Placeholder for a revision already applied in this database.

The live database is stamped 0005_dataset_research_fields, but that migration
file was not present in this checkout. This no-op keeps the Alembic chain
intact so later revisions can run.
"""

revision = "0005_dataset_research_fields"
down_revision = "0004_integration_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
