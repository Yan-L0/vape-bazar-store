from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Order, OrderContactMethod, OrderItem, OrderStatus, Product


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_order(
        self,
        *,
        telegram_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
        customer_name: str,
        contact_username: str,
        phone: str | None,
        comment: str | None,
        contact_method: OrderContactMethod,
        items: list[tuple[Product, int]],
    ) -> Order:
        order = Order(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_first_name=telegram_first_name,
            customer_name=customer_name,
            contact_username=contact_username,
            phone=phone,
            comment=comment,
            contact_method=contact_method,
            total_amount=sum(product.price * quantity for product, quantity in items),
        )
        order.items = [
            OrderItem(
                product_id=product.id,
                product_title=product.title,
                price=product.price,
                quantity=quantity,
            )
            for product, quantity in items
        ]
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["items"])
        return order

    async def get_order(self, order_id: int, *, for_update: bool = False) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        await self.session.flush()
        return order
