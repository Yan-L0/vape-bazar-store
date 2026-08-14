from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import ADMIN_MENU_ADD
from app.database.models import ProductCategory, ProductStatus
from app.handlers.admin.helpers import is_admin, send_preview
from app.keyboards.admin import (
    AdminAddCategoryCallback,
    AdminConditionCallback,
    AdminEditFieldCallback,
    AdminPreviewActionCallback,
    admin_menu_keyboard,
    category_inline_keyboard,
    condition_inline_keyboard,
    description_inline_keyboard,
    edit_fields_keyboard,
    photo_collection_keyboard,
)
from app.services import formatter
from app.services.exceptions import ChannelOperationError, InvalidPriceError
from app.services.product_service import ProductDraft, ProductService
from app.states.product_states import ProductStates

router = Router(name="admin_add_product")

REQUIRED_DRAFT_FIELDS = {"photo_file_ids", "title", "size", "price", "stock_quantity", "condition", "category"}
FLOW_START_MESSAGE_ID_KEY = "product_flow_start_message_id"


@router.message(F.text == ADMIN_MENU_ADD)
async def start_add_product_handler(
    message: Message,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    await state.clear()
    await state.set_state(ProductStates.waiting_for_photos)
    await state.update_data(
        photo_file_ids=[],
        status=ProductStatus.ACTIVE.value,
        **{FLOW_START_MESSAGE_ID_KEY: message.message_id},
    )
    await product_service.record_admin_action(admin_id=message.from_user.id, action="START_ADD_PRODUCT")
    await _safe_delete_message(message)
    await message.answer(
        formatter.format_photo_prompt(),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=False),
    )


@router.callback_query(F.data == "admin:add")
async def start_add_product_callback_handler(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await state.clear()
    await state.set_state(ProductStates.waiting_for_photos)
    await state.update_data(
        photo_file_ids=[],
        status=ProductStatus.ACTIVE.value,
        **{FLOW_START_MESSAGE_ID_KEY: callback.message.message_id},
    )
    await product_service.record_admin_action(admin_id=callback.from_user.id, action="START_ADD_PRODUCT")
    await callback.answer()
    await callback.message.edit_text(
        formatter.format_photo_prompt(),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=False),
    )


@router.message(ProductStates.waiting_for_photos, F.photo)
@router.message(ProductStates.editing_photos, F.photo)
async def product_photo_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids: list[str] = list(data.get("photo_file_ids", []))
    if len(photo_file_ids) >= 5:
        await _safe_delete_message(message)
        await message.answer(formatter.format_photo_limit_message(), parse_mode="HTML")
        return

    photo_file_id = message.photo[-1].file_id
    await _safe_delete_message(message)
    if photo_file_id in photo_file_ids:
        await message.answer(
            formatter.format_photo_saved_message(len(photo_file_ids)),
            parse_mode="HTML",
            reply_markup=photo_collection_keyboard(can_finish=True),
        )
        return

    photo_file_ids.append(photo_file_id)
    await state.update_data(photo_file_ids=photo_file_ids)
    await message.answer(
        formatter.format_photo_saved_message(len(photo_file_ids)),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=True),
    )


@router.message(ProductStates.waiting_for_photos)
@router.message(ProductStates.editing_photos)
async def product_photo_invalid_input_handler(message: Message) -> None:
    await _safe_delete_message(message)
    await message.answer(formatter.format_photo_prompt(), parse_mode="HTML")


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "photos_done"))
async def photo_collection_done_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    photo_file_ids: list[str] = list(data.get("photo_file_ids", []))
    if not photo_file_ids:
        await callback.answer("Сначала добавьте хотя бы одно фото.", show_alert=True)
        return

    current_state = await state.get_state()
    await callback.answer()
    if current_state == ProductStates.editing_photos.state:
        await state.set_state(ProductStates.preview)
        await send_preview(callback, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_title)
    await callback.message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")


@router.message(ProductStates.waiting_for_title)
@router.message(ProductStates.editing_title)
async def title_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await _safe_delete_message(message)
        await message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")
        return

    value = message.text.strip()
    await _safe_delete_message(message)
    await state.update_data(title=value)
    if await state.get_state() == ProductStates.editing_title.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_size)
    await message.answer(formatter.format_enter_size_prompt())


@router.message(ProductStates.waiting_for_size)
@router.message(ProductStates.editing_size)
async def size_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await _safe_delete_message(message)
        await message.answer(formatter.format_enter_size_prompt())
        return

    value = message.text.strip()
    await _safe_delete_message(message)
    await state.update_data(size=value)
    if await state.get_state() == ProductStates.editing_size.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_price)
    await message.answer(formatter.format_enter_price_prompt())


@router.message(ProductStates.waiting_for_price)
@router.message(ProductStates.editing_price)
async def price_handler(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not message.text:
        await _safe_delete_message(message)
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    text = message.text.strip()
    await _safe_delete_message(message)
    if not text.isdigit():
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    current_state = await state.get_state()
    price = int(text)
    await state.update_data(price=price)

    if current_state == ProductStates.editing_price.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_quantity)
    await message.answer(formatter.format_enter_quantity_prompt())


@router.message(ProductStates.waiting_for_quantity)
@router.message(ProductStates.editing_quantity)
async def quantity_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    text = (message.text or "").strip()
    await _safe_delete_message(message)
    if not text.isdigit() or int(text) <= 0:
        await message.answer(formatter.format_invalid_quantity_message())
        return

    current_state = await state.get_state()
    await state.update_data(stock_quantity=int(text))
    if current_state == ProductStates.editing_quantity.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_condition)
    await message.answer(formatter.format_enter_condition_prompt(), reply_markup=condition_inline_keyboard())


@router.message(ProductStates.waiting_for_condition)
@router.message(ProductStates.editing_condition)
async def condition_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    await _safe_delete_message(message)
    await message.answer(formatter.format_enter_condition_prompt(), reply_markup=condition_inline_keyboard())


@router.callback_query(AdminConditionCallback.filter())
async def condition_selected_handler(
    callback: CallbackQuery,
    callback_data: AdminConditionCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    if callback_data.value not in {"Новый", "Б/у"}:
        await callback.answer("Выберите состояние кнопкой.", show_alert=True)
        return
    current_state = await state.get_state()
    if current_state not in {ProductStates.waiting_for_condition.state, ProductStates.editing_condition.state}:
        await callback.answer("Этот шаг уже завершён.")
        return
    await state.update_data(condition=callback_data.value)
    await callback.answer()
    if current_state == ProductStates.editing_condition.state:
        await state.set_state(ProductStates.preview)
        await send_preview(callback, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_description)
    await callback.message.edit_text(
        formatter.format_enter_description_prompt(),
        reply_markup=description_inline_keyboard(),
    )


@router.message(ProductStates.waiting_for_description)
@router.message(ProductStates.editing_description)
async def description_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await _safe_delete_message(message)
        await message.answer(
            formatter.format_enter_description_prompt(),
            reply_markup=description_inline_keyboard(),
        )
        return

    value = message.text.strip()
    await _safe_delete_message(message)
    await state.update_data(description=value)
    if await state.get_state() == ProductStates.editing_description.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_category)
    await message.answer(
        formatter.format_choose_category_prompt(),
        reply_markup=category_inline_keyboard(),
    )


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "description_skip"))
async def description_skip_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    current_state = await state.get_state()
    if current_state not in {ProductStates.waiting_for_description.state, ProductStates.editing_description.state}:
        await callback.answer("Этот шаг уже завершён.")
        return
    await state.update_data(description="0")
    await callback.answer()
    if current_state == ProductStates.editing_description.state:
        await state.set_state(ProductStates.preview)
        await send_preview(callback, state, settings)
        return
    await state.set_state(ProductStates.waiting_for_category)
    await callback.message.edit_text(
        formatter.format_choose_category_prompt(),
        reply_markup=category_inline_keyboard(),
    )


@router.message(ProductStates.waiting_for_category)
@router.message(ProductStates.editing_category)
async def category_text_rejected_handler(message: Message) -> None:
    await _safe_delete_message(message)
    await message.answer(formatter.format_invalid_category_message(), parse_mode="HTML")


@router.callback_query(AdminAddCategoryCallback.filter())
async def category_selected_handler(
    callback: CallbackQuery,
    callback_data: AdminAddCategoryCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    try:
        ProductCategory(callback_data.category)
    except ValueError:
        await callback.answer()
        await callback.message.answer(formatter.format_invalid_category_message(), parse_mode="HTML")
        return

    data = await state.get_data()
    if not {"photo_file_ids", "title", "size", "price", "stock_quantity", "condition"}.issubset(data.keys()):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    await state.update_data(category=callback_data.category, status=ProductStatus.ACTIVE.value)
    await state.set_state(ProductStates.preview)
    await callback.answer()
    await send_preview(callback, state, settings)


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "edit"))
async def edit_preview_handler(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=edit_fields_keyboard())


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "back_to_preview"))
async def back_to_preview_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    await callback.answer()
    if not _has_complete_draft(data):
        await state.clear()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    await state.set_state(ProductStates.preview)
    await send_preview(callback, state, settings)


@router.callback_query(AdminEditFieldCallback.filter())
async def edit_field_handler(
    callback: CallbackQuery,
    callback_data: AdminEditFieldCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    field = callback_data.field
    await callback.answer()
    if field == "photos":
        await state.update_data(photo_file_ids=[])
        await state.set_state(ProductStates.editing_photos)
        await callback.message.answer(
            "Отправьте новые фотографии товара. Они заменят текущие фото.",
            reply_markup=photo_collection_keyboard(can_finish=False),
        )
        return
    if field == "title":
        await state.set_state(ProductStates.editing_title)
        await callback.message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")
        return
    if field == "size":
        await state.set_state(ProductStates.editing_size)
        await callback.message.answer(formatter.format_enter_size_prompt())
        return
    if field == "price":
        await state.set_state(ProductStates.editing_price)
        await callback.message.answer(formatter.format_enter_price_prompt())
        return
    if field == "quantity":
        await state.set_state(ProductStates.editing_quantity)
        await callback.message.answer(formatter.format_enter_quantity_prompt())
        return
    if field == "condition":
        await state.set_state(ProductStates.editing_condition)
        await callback.message.answer(formatter.format_enter_condition_prompt(), reply_markup=condition_inline_keyboard())
        return
    if field == "description":
        await state.set_state(ProductStates.editing_description)
        await callback.message.answer(
            formatter.format_enter_description_prompt(),
            reply_markup=description_inline_keyboard(),
        )
        return
    if field == "category":
        await state.set_state(ProductStates.editing_category)
        await callback.message.answer(
            formatter.format_choose_category_prompt(),
            reply_markup=category_inline_keyboard(),
        )
        return

    await callback.message.answer(
        formatter.format_cancelled_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "publish"))
@router.callback_query(AdminPreviewActionCallback.filter(F.action == "save_bot_only"))
async def publish_product_handler(
    callback: CallbackQuery,
    callback_data: AdminPreviewActionCallback,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    if not _has_complete_draft(data):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    try:
        draft = ProductDraft(
            title=data["title"],
            size=data["size"],
            condition=data["condition"],
            description=data.get("description"),
            category=ProductCategory(data["category"]),
            price=int(data["price"]),
            stock_quantity=int(data["stock_quantity"]),
            photo_file_ids=list(data["photo_file_ids"]),
        )
    except (TypeError, ValueError):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    try:
        await product_service.publish_product(
            admin_id=callback.from_user.id,
            draft=draft,
            publish_to_channel=callback_data.action == "publish",
        )
    except ChannelOperationError:
        await callback.answer()
        await callback.message.answer(formatter.format_channel_error_message(), parse_mode="HTML")
        return
    except InvalidPriceError:
        await callback.answer()
        await callback.message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    await _cleanup_creation_messages(callback, state)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        formatter.format_product_published_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "cancel"))
async def cancel_add_product_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await _cleanup_creation_messages(callback, state)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        formatter.format_cancelled_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


def _has_complete_draft(data: dict) -> bool:
    if not REQUIRED_DRAFT_FIELDS.issubset(data.keys()):
        return False
    if not isinstance(data.get("photo_file_ids"), list) or not data["photo_file_ids"]:
        return False
    return True


async def _safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        return


async def _cleanup_creation_messages(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    start_message_id = data.get(FLOW_START_MESSAGE_ID_KEY)
    if not isinstance(start_message_id, int) or callback.message is None:
        return
    end_message_id = callback.message.message_id
    if end_message_id < start_message_id or end_message_id - start_message_id > 100:
        return
    for message_id in range(start_message_id, end_message_id + 1):
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=message_id)
        except TelegramAPIError:
            continue
