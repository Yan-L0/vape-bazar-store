from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.styles import STYLE_PRIMARY, STYLE_SUCCESS, add_inline_button


class OrderActionCallback(CallbackData, prefix="order_action"):
    action: str
    order_id: int


def order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text="Оставить заказ",
        callback_data=OrderActionCallback(action="keep", order_id=order_id),
        style=STYLE_PRIMARY,
    )
    add_inline_button(
        builder,
        text="Куплен",
        callback_data=OrderActionCallback(action="purchase", order_id=order_id),
        style=STYLE_SUCCESS,
    )
    builder.adjust(2)
    return builder.as_markup()
