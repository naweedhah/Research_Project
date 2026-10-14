"""Initial schema, indexes, grants and row-level security."""

from alembic import op
import sqlalchemy as sa

from app.core.db import Base
from app.models import *  # noqa: F403

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    op.execute("CREATE INDEX IF NOT EXISTS ix_children_facility_pseudo ON children (facility_id, pseudonymous_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_visits_child_date ON visits (child_id, visit_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_facility_status ON alerts (facility_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_predictions_visit_active ON predictions (visit_id, is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON audit_logs (timestamp)")

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnip_app') THEN
            GRANT USAGE ON SCHEMA public TO cnip_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cnip_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cnip_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cnip_app;
          END IF;
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnip_readonly') THEN
            GRANT USAGE ON SCHEMA public TO cnip_readonly;
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO cnip_readonly;
            REVOKE SELECT ON caregivers FROM cnip_readonly;
          END IF;
        END $$;
        """
    )

    # Facility-scoped RLS. Application still enforces RBAC; RLS is defense in depth.
    for table in ("children", "visits", "alerts", "follow_up_schedules"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_facility_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_facility_isolation ON {table}
            USING (
              current_setting('app.rls_bypass', true) = '1'
              OR facility_id::text = current_setting('app.facility_id', true)
            )
            WITH CHECK (
              current_setting('app.rls_bypass', true) = '1'
              OR facility_id::text = current_setting('app.facility_id', true)
            )
            """
        )

    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS audit_logs_insert_only ON audit_logs")
    op.execute(
        """
        CREATE POLICY audit_logs_insert_only ON audit_logs
        FOR INSERT WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_logs_select ON audit_logs
        FOR SELECT USING (true)
        """
    )
    # No UPDATE/DELETE policies — audit records are immutable via RLS.


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
