from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.database.models import Order, OrderItem, OrderStatus, Product, ProductCategory, ProductStatus
from app.keyboards.orders import order_actions_keyboard
from app.services.order_service import OrderService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeProducts:
    def __init__(self, product: Product) -> None:
        self.product = product

    async def get_product(self, product_id: int, *, for_update: bool = False):
        return self.product if product_id == self.product.id else None


class FakeOrders:
    def __init__(self, order: Order) -> None:
        self.order = order

    async def get_order(self, order_id: int, *, for_update: bool = False):
        return self.order if order_id == self.order.id else None

    async def set_status(self, order: Order, status: OrderStatus):
        order.status = status
        return order


def build_service(*, stock_quantity: int, ordered_quantity: int = 1):
    product = Product(
        id=7,
        title="POD Test",
        size="Black",
        condition="Новый",
        category=ProductCategory.POD_SYSTEMS,
        price=1500,
        stock_quantity=stock_quantity,
        status=ProductStatus.ACTIVE,
    )
    order = Order(id=11, status=OrderStatus.PENDING)
    order.items = [
        OrderItem(product_id=product.id, product_title=product.title, price=product.price, quantity=ordered_quantity)
    ]
    session = FakeSession()
    service = OrderService(
        session=session,
        settings=SimpleNamespace(),
        products=FakeProducts(product),
        users=SimpleNamespace(),
        orders=FakeOrders(order),
    )
    return service, session, product, order


@pytest.mark.asyncio
async def test_purchase_decrements_stock_and_reports_depleted_product() -> None:
    service, session, product, order = build_service(stock_quantity=2, ordered_quantity=2)

    purchased, depleted = await service.purchase_order(order.id)

    assert purchased.status == OrderStatus.PURCHASED
    assert product.stock_quantity == 0
    assert depleted == [product.id]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_keep_order_does_not_change_stock() -> None:
    service, session, product, order = build_service(stock_quantity=4)

    kept = await service.keep_order(order.id)

    assert kept.status == OrderStatus.KEPT
    assert product.stock_quantity == 4
    assert session.commits == 1


def test_order_keyboard_has_requested_actions() -> None:
    labels = [button.text for row in order_actions_keyboard(42).inline_keyboard for button in row]
    assert labels == ["Оставить заказ", "Куплен"]
