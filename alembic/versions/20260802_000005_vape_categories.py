from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260802_000005"
down_revision = "20260428_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires new enum values to be committed before they are used.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE product_category ADD VALUE IF NOT EXISTS 'POD_SYSTEMS'")
        op.execute("ALTER TYPE product_category ADD VALUE IF NOT EXISTS 'LIQUIDS'")

    op.execute(
        "UPDATE products SET category = 'POD_SYSTEMS' "
        "WHERE category::text IN ('SHOES', 'CLOTHING', 'ACCESSORIES')"
    )


def downgrade() -> None:
    # Enum labels cannot be removed safely. Keeping the unused labels makes the
    # downgrade data-safe and lets the previous application version read rows.
    op.execute("UPDATE products SET category = 'SHOES' WHERE category::text = 'POD_SYSTEMS'")
    op.execute("UPDATE products SET category = 'CLOTHING' WHERE category::text = 'LIQUIDS'")
