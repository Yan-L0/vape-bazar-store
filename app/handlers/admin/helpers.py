from __future__ import annotations

from typing import cast

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from app.config import Settings
from app.database.models import Product, ProductCategory, ProductPhoto, ProductStatus
from app.keyboards.admin import preview_actions_keyboard
from app.services import formatter


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


async def replace_admin_message(
    message: Message,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str | None = None,
) -> Message | None:
    """Keep admin navigation in one chat position instead of stacking messages."""
    if message.text is not None:
        try:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return message
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return message

    try:
        await message.delete()
    except TelegramAPIError:
        pass
    return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


def build_draft_product(data: dict) -> Product:
    category = data.get("category")
    if isinstance(category, str):
        category = ProductCategory(category)
    product = Product(
        title=data.get("title", ""),
        size=data.get("size", ""),
        condition=data.get("condition", ""),
        description=data.get("description"),
        category=cast(ProductCategory, category),
        price=int(data.get("price", 0) or 0),
        stock_quantity=int(data.get("stock_quantity", 1) or 1),
        old_price=data.get("old_price"),
        status=ProductStatus(data.get("status", ProductStatus.ACTIVE.value)),
    )
    product.photos = [
        ProductPhoto(file_id=file_id, sort_order=index)
        for index, file_id in enumerate(_unique_file_ids(data.get("photo_file_ids", [])), start=1)
    ]
    return product


async def send_preview(target: Message | CallbackQuery, state: FSMContext, settings: Settings) -> None:
    data = await state.get_data()
    product = build_draft_product(data)
    text = formatter.format_admin_preview(product, settings.support_username)
    photo_file_ids = _unique_file_ids(data.get("photo_file_ids", []))
    await send_photo_or_text(
        target,
        text=text,
        photo_file_ids=photo_file_ids,
        reply_markup=preview_actions_keyboard(),
    )


async def send_photo_or_text(
    target: Message | CallbackQuery,
    *,
    text: str,
    photo_file_id: str | None = None,
    photo_file_ids: list[str] | None = None,
    reply_markup=None,
) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    file_ids = _unique_file_ids(photo_file_ids or ([photo_file_id] if photo_file_id else []))
    if len(file_ids) > 1:
        media = [
            InputMediaPhoto(
                media=file_id,
                caption=text if index == 0 else None,
                parse_mode="HTML" if index == 0 else None,
            )
            for index, file_id in enumerate(file_ids)
        ]
        await message.answer_media_group(media=media)
        await message.answer("Выберите действие:", reply_markup=reply_markup)
        return
    if file_ids:
        await message.answer_photo(
            photo=file_ids[0],
            caption=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        return
    await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)


def _unique_file_ids(file_ids: list[str]) -> list[str]:
    return list(dict.fromkeys(file_ids))
