from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import ADMIN_MENU_ARCHIVE
from app.handlers.admin.helpers import is_admin, replace_admin_message
from app.keyboards.admin import AdminProductActionCallback, admin_back_keyboard, archived_products_keyboard
from app.services import formatter
from app.services.exceptions import ProductNotFoundError
from app.services.product_service import ProductService
from app.states.product_states import ProductStates

router = Router(name="admin_archive")


@router.message(F.text == ADMIN_MENU_ARCHIVE)
async def archive_message_handler(message: Message, settings: Settings, product_service: ProductService) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return
    await _show_archive(message, product_service, 1)


@router.callback_query(F.data.startswith("admin:archive"))
async def archive_callback_handler(callback: CallbackQuery, settings: Settings, product_service: ProductService) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    parts = (callback.data or "").split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    await callback.answer()
    await _show_archive(callback.message, product_service, page, replace=True)


@router.callback_query(AdminProductActionCallback.filter(F.action == "restore"))
async def restore_start_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    state: FSMContext,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    await state.set_state(ProductStates.waiting_for_restore_quantity)
    await state.update_data(restore_product_id=callback_data.product_id)
    await callback.answer()
    await callback.message.answer("Сколько штук вернуть в продажу? Введите целое число больше нуля.")


@router.message(ProductStates.waiting_for_restore_quantity)
async def restore_quantity_handler(
    message: Message,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return
    value = (message.text or "").strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer(formatter.format_invalid_quantity_message())
        return
    data = await state.get_data()
    product_id = data.get("restore_product_id")
    if not isinstance(product_id, int):
        await state.clear()
        await message.answer("Не удалось определить товар. Откройте архив и попробуйте снова.")
        return
    try:
        product = await product_service.restore_product(
            admin_id=message.from_user.id,
            product_id=product_id,
            stock_quantity=int(value),
        )
    except ProductNotFoundError:
        await state.clear()
        await message.answer(formatter.format_product_not_found_message())
        return
    await state.clear()
    await message.answer(f"Товар «{product.title}» возвращён в продажу: {product.stock_quantity} шт.")


async def _show_archive(
    message: Message,
    product_service: ProductService,
    page: int,
    *,
    replace: bool = False,
) -> None:
    result = await product_service.list_archived_products(page=page)
    if not result.items:
        if replace:
            await replace_admin_message(
                message,
                "Архив товаров пуст.",
                reply_markup=admin_back_keyboard(),
            )
        else:
            await message.answer("Архив товаров пуст.", reply_markup=admin_back_keyboard())
        return
    markup = archived_products_keyboard(
        products=result.items,
        page=result.page,
        total_pages=result.total_pages,
    )
    text = "Архив товаров. Нажмите на товар, чтобы вернуть его в продажу:"
    if replace:
        await replace_admin_message(message, text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)
