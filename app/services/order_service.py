from __future__ import annotations

from dataclasses import dataclass
from html import escape

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Order, OrderContactMethod, OrderStatus, ProductStatus
from app.database.repositories.orders import OrderRepository
from app.database.repositories.products import ProductRepository
from app.database.repositories.users import UserRepository
from app.utils.logging import get_logger
from app.keyboards.orders import order_actions_keyboard


@dataclass(slots=True)
class OrderDraftItem:
    product_id: int
    quantity: int


@dataclass(slots=True)
class TelegramCustomer:
    telegram_id: int
    username: str | None
    first_name: str | None


class OrderValidationError(Exception):
    """Raised when order payload is invalid."""


class OrderService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        products: ProductRepository,
        users: UserRepository,
        orders: OrderRepository,
    ) -> None:
        self.session = session
        self.settings = settings
        self.products = products
        self.users = users
        self.orders = orders
        self.logger = get_logger("app.order_service")

    async def create_order(
        self,
        *,
        customer: TelegramCustomer,
        name: str | None,
        username: str,
        phone: str | None,
        comment: str | None,
        contact_method: OrderContactMethod,
        items: list[OrderDraftItem],
    ) -> Order:
        if not items:
            raise OrderValidationError("Корзина пуста.")

        if customer.telegram_id > 0:
            await self.users.upsert_user(
                telegram_id=customer.telegram_id,
                username=customer.username,
                first_name=customer.first_name,
            )

        normalized_username = self._normalize_username(username)
        customer_name = (name or customer.first_name or normalized_username.lstrip("@")).strip()
        normalized_phone = phone.strip() if phone and phone.strip() else None
        if contact_method in {OrderContactMethod.PHONE, OrderContactMethod.WHATSAPP} and not normalized_phone:
            raise OrderValidationError("Для выбранного способа связи нужно указать телефон.")

        product_map = {product.id: product for product in await self.products.get_products_by_ids([item.product_id for item in items])}
        if len(product_map) != len({item.product_id for item in items}):
            raise OrderValidationError("Некоторые товары уже недоступны.")

        normalized_items: list[tuple] = []
        for item in items:
            product = product_map.get(item.product_id)
            if product is None or product.archived_at is not None:
                raise OrderValidationError("Некоторые товары уже недоступны.")
            if product.status == ProductStatus.SOLD:
                raise OrderValidationError(f"Товар «{product.title}» уже продан.")
            if item.quantity < 1:
                raise OrderValidationError("Количество товара должно быть больше нуля.")
            if item.quantity > product.stock_quantity:
                raise OrderValidationError(
                    f"Для товара «{product.title}» доступно только {product.stock_quantity} шт."
                )
            normalized_items.append((product, item.quantity))

        order = await self.orders.create_order(
            telegram_id=customer.telegram_id,
            telegram_username=customer.username,
            telegram_first_name=customer.first_name,
            customer_name=customer_name,
            contact_username=normalized_username,
            phone=normalized_phone,
            comment=comment.strip() if comment and comment.strip() else None,
            contact_method=contact_method,
            items=normalized_items,
        )
        await self.session.commit()
        await self.session.refresh(order, attribute_names=["items"])
        await self._notify_admins(order, customer=customer)
        return order

    async def _notify_admins(self, order: Order, *, customer: TelegramCustomer) -> None:
        bot = Bot(
            token=self.settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        message = self._format_admin_order_message(order, customer=customer)
        try:
            targets = [self.settings.order_channel_id] if self.settings.order_channel_id else list(self.settings.admin_ids)
            for chat_id in targets:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=order_actions_keyboard(order.id),
                )
        except Exception:
            self.logger.exception("order_admin_notification_failed", order_id=order.id)
        finally:
            await bot.session.close()

    @staticmethod
    def _normalize_username(username: str) -> str:
        cleaned = username.strip()
        if not cleaned:
            raise OrderValidationError("Укажите username для связи.")
        return cleaned if cleaned.startswith("@") else f"@{cleaned}"

    async def keep_order(self, order_id: int) -> Order:
        order = await self.orders.get_order(order_id, for_update=True)
        if order is None:
            raise OrderValidationError("Заказ не найден.")
        if order.status == OrderStatus.PURCHASED:
            raise OrderValidationError("Заказ уже отмечен как купленный.")
        await self.orders.set_status(order, OrderStatus.KEPT)
        await self.session.commit()
        return order

    async def purchase_order(self, order_id: int) -> tuple[Order, list[int]]:
        order = await self.orders.get_order(order_id, for_update=True)
        if order is None:
            raise OrderValidationError("Заказ не найден.")
        if order.status == OrderStatus.PURCHASED:
            return order, []

        depleted_product_ids: list[int] = []
        for item in order.items:
            if item.product_id is None:
                raise OrderValidationError(f"Товар «{item.product_title}» удалён и не может быть списан.")
            product = await self.products.get_product(item.product_id, for_update=True)
            if product is None or product.archived_at is not None or product.status == ProductStatus.SOLD:
                raise OrderValidationError(f"Товар «{item.product_title}» уже недоступен.")
            if product.stock_quantity < item.quantity:
                raise OrderValidationError(
                    f"Недостаточно товара «{item.product_title}»: осталось {product.stock_quantity} шт."
                )
            product.stock_quantity -= item.quantity
            if product.stock_quantity == 0:
                depleted_product_ids.append(product.id)

        await self.orders.set_status(order, OrderStatus.PURCHASED)
        await self.session.commit()
        return order, depleted_product_ids

    @staticmethod
    def _format_admin_order_message(order: Order, *, customer: TelegramCustomer) -> str:
        contact_labels = {
            OrderContactMethod.TELEGRAM: "Telegram",
            OrderContactMethod.PHONE: "Телефон",
            OrderContactMethod.WHATSAPP: "WhatsApp",
        }
        telegram_name = customer.first_name or "Покупатель"
        customer_link = (
            f'<a href="tg://user?id={customer.telegram_id}">{escape(telegram_name)}</a>'
            if customer.telegram_id > 0
            else "<b>не передан через Telegram Mini App</b>"
        )
        telegram_username_line = f"Telegram username: <b>@{escape(customer.username)}</b>\n" if customer.username else ""
        phone_line = f"Телефон: <b>{escape(order.phone)}</b>\n" if order.phone else ""
        items_text = "\n".join(f"• <b>{escape(item.product_title)}</b> — {item.quantity} шт. × {item.price} ₽" for item in order.items)
        return (
            f"<b>Новый заказ #{order.id}</b>\n\n"
            f"Telegram: {customer_link}\n"
            f"{telegram_username_line}"
            f"Telegram ID: <code>{customer.telegram_id if customer.telegram_id > 0 else 'неизвестно'}</code>\n"
            f"Username для связи: <b>{escape(order.contact_username)}</b>\n"
            f"{phone_line}"
            f"Способ связи: <b>{contact_labels[order.contact_method]}</b>\n\n"
            f"<b>Товары:</b>\n{items_text}\n\n"
            f"Итого: <b>{order.total_amount} ₽</b>"
        )
