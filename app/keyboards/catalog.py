from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import BUTTON_WRITE_ADMIN, CATEGORY_ORDER, MAIN_MENU_BACK
from app.database.models import Product, ProductCategory
from app.keyboards.styles import STYLE_PRIMARY, add_inline_button
from app.utils import premium_emoji as emoji

POD_SYSTEMS_BUTTON_EMOJI_ID = "5355227496830743755"
LIQUIDS_BUTTON_EMOJI_ID = "5204249655390525007"

CATEGORY_EMOJI_IDS = {
    ProductCategory.POD_SYSTEMS: POD_SYSTEMS_BUTTON_EMOJI_ID,
    ProductCategory.LIQUIDS: LIQUIDS_BUTTON_EMOJI_ID,
    ProductCategory.CARTRIDGES_COILS: emoji.MEDIA_ID,
    ProductCategory.SNUS_PLATES: emoji.TAG_ID,
    ProductCategory.DISPOSABLES: emoji.FIRE_ID,
}


class CatalogCategoryCallback(CallbackData, prefix="catalog_category"):
    category: str


class CatalogListCallback(CallbackData, prefix="catalog_list"):
    category: str
    page: int


class CatalogProductCallback(CallbackData, prefix="catalog_product"):
    product_id: int
    category: str
    page: int


def catalog_categories_keyboard(*, reviews_url: str | None = None, support_url: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in CATEGORY_ORDER:
        add_inline_button(
            builder,
            text=category.label,
            callback_data=CatalogCategoryCallback(category=category.value),
            icon_custom_emoji_id=CATEGORY_EMOJI_IDS[category],
        )
    if reviews_url:
        add_inline_button(
            builder,
            text="Отзывы",
            url=reviews_url,
            style=STYLE_PRIMARY,
            icon_custom_emoji_id=emoji.SHIELD_ID,
        )
    if support_url:
        add_inline_button(
            builder,
            text="Поддержка",
            url=support_url,
            style=STYLE_PRIMARY,
            icon_custom_emoji_id=emoji.USER_ID,
        )
    add_inline_button(builder, text=MAIN_MENU_BACK, callback_data="main:home", icon_custom_emoji_id=emoji.REFRESH_ID)
    builder.adjust(1)
    return builder.as_markup()


def catalog_products_keyboard(
    *,
    products: list[Product],
    category: ProductCategory,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product.title} — {product.price} ₽",
            callback_data=CatalogProductCallback(product_id=product.id, category=category.value, page=page),
        )
    builder.adjust(1)

    if total_pages > 1:
        if page > 1:
            builder.button(
                text="⬅️",
                callback_data=CatalogListCallback(category=category.value, page=page - 1),
            )
        builder.button(text=f"{page}/{total_pages}", callback_data="catalog:noop")
        if page < total_pages:
            builder.button(
                text="➡️",
                callback_data=CatalogListCallback(category=category.value, page=page + 1),
            )
        builder.adjust(1, 3)

    add_inline_button(builder, text="Назад", callback_data="catalog:categories", icon_custom_emoji_id=emoji.REFRESH_ID)
    return builder.as_markup()


def product_detail_keyboard(
    *,
    support_url: str,
    category: ProductCategory,
    page: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(builder, text=BUTTON_WRITE_ADMIN, url=support_url, style=STYLE_PRIMARY, icon_custom_emoji_id=emoji.USER_ID)
    add_inline_button(
        builder,
        text="Назад",
        callback_data=CatalogListCallback(category=category.value, page=page),
        icon_custom_emoji_id=emoji.REFRESH_ID,
    )
    builder.adjust(1)
    return builder.as_markup()
