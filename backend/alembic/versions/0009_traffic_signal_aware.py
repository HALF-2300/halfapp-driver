"""Add traffic_signal_aware to rides for free official traffic signals v0.1."""

from alembic import op

revision = "0009_traffic_signal_aware"
down_revision = "0008_pricing_policy_and_ledger_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE rides ADD COLUMN traffic_signal_aware INTEGER"
        )
    else:
        op.execute(
            "ALTER TABLE rides ADD COLUMN traffic_signal_aware BOOLEAN"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot drop columns easily in older versions; leave no-op for dev rollback
        pass
    else:
        op.drop_column("rides", "traffic_signal_aware")
