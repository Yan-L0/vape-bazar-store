from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260804_000007"
down_revision = "20260802_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE product_category ADD VALUE IF NOT EXISTS 'CARTRIDGES_COILS'")
        op.execute("ALTER TYPE product_category ADD VALUE IF NOT EXISTS 'SNUS_PLATES'")
        op.execute("ALTER TYPE product_category ADD VALUE IF NOT EXISTS 'DISPOSABLES'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely while products may use them.
    pass
