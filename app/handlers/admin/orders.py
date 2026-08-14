from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.config import Settings
from app.handlers.admin.helpers import is_admin
from app.keyboards.orders import OrderActionCallback
from app.services.order_service import OrderService, OrderValidationError
from app.services.product_service import ProductService

router = Router(name="admin_orders")


@router.callback_query(OrderActionCallback.filter())
async def order_action_handler(
    callback: CallbackQuery,
    callback_data: OrderActionCallback,
    settings: Settings,
    order_service: OrderService,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    try:
        if callback_data.action == "keep":
            await order_service.keep_order(callback_data.order_id)
            status_text = "ОСТАВЛЕН"
        elif callback_data.action == "purchase":
            _, depleted_ids = await order_service.purchase_order(callback_data.order_id)
            for product_id in depleted_ids:
                await product_service.mark_as_sold(
                    admin_id=callback.from_user.id,
                    product_id=product_id,
                    allow_channel_failure=True,
                )
            status_text = "КУПЛЕН"
        else:
            await callback.answer("Неизвестное действие.", show_alert=True)
            return
    except OrderValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer(f"Заказ #{callback_data.order_id}: {status_text.lower()}.")
    if callback.message:
        current_text = callback.message.html_text or callback.message.text or ""
        if "\n\n<b>Статус:" in current_text:
            current_text = current_text.split("\n\n<b>Статус:", 1)[0]
        await callback.message.edit_text(
            f"{current_text}\n\n<b>Статус: {status_text}</b>",
            reply_markup=None,
        )
