from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260802_000006"
down_revision = "20260802_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    order_status = postgresql.ENUM(
        "PENDING",
        "KEPT",
        "PURCHASED",
        name="order_status",
        create_type=False,
    )
    order_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "products",
        sa.Column("stock_quantity", sa.Integer(), server_default="1", nullable=False),
    )
    op.execute("UPDATE products SET stock_quantity = 0 WHERE status::text = 'SOLD'")

    op.add_column(
        "orders",
        sa.Column("status", order_status, server_default="PENDING", nullable=False),
    )
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_column("orders", "status")
    op.drop_column("products", "stock_quantity")
    sa.Enum(name="order_status").drop(op.get_bind(), checkfirst=True)
