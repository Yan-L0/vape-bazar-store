from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.database.models import ProductCategory
from app.handlers.admin.add_product import publish_product_handler
from app.handlers.admin.admin_panel import admin_panel_handler
from app.handlers.admin.archive import archive_callback_handler
from app.handlers.admin.import_channel import _infer_category
from app.handlers.user.support import reviews_handler
from app.keyboards.admin import AdminPreviewActionCallback
from app.services import formatter


class DummyState:
    async def clear(self) -> None:
        return None


class DummyProductService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    async def record_admin_action(self, *, admin_id: int, action: str, product_id=None) -> None:
        self.calls.append((admin_id, action))


class ProductDraftState:
    def __init__(self) -> None:
        self.cleared = False

    async def get_data(self) -> dict:
        return {
            "photo_file_ids": ["photo-1"],
            "title": "Test product",
            "size": "30 ml",
            "price": 990,
            "stock_quantity": 3,
            "condition": "New",
            "description": "Test description",
            "category": ProductCategory.POD_SYSTEMS.value,
        }

    async def clear(self) -> None:
        self.cleared = True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Картридж 0.8 Ом", ProductCategory.CARTRIDGES_COILS),
        ("Снюс и никотиновые пластинки", ProductCategory.SNUS_PLATES),
        ("Одноразовое электронное устройство", ProductCategory.DISPOSABLES),
        ("POD-система", ProductCategory.POD_SYSTEMS),
        ("Жидкость 30 мл", ProductCategory.LIQUIDS),
    ],
)
def test_import_infers_all_product_categories(text: str, expected: ProductCategory) -> None:
    assert _infer_category(text) == expected


def build_settings() -> Settings:
    return Settings(
        BOT_TOKEN="token",
        ADMIN_IDS="1,2",
        CHANNEL_ID=-1001234567890,
        SUPPORT_USERNAME="demo_support",
        SUPPORT_URL="https://t.me/demo_support",
        REVIEWS_URL="https://t.me/demo_reviews",
        TIKTOK_URL="https://example.com/tiktok",
        LOGISTICS_URL="https://t.me/demo_channel/1",
        POSTGRES_HOST="postgres",
        POSTGRES_PORT=5432,
        POSTGRES_DB="store_manager",
        POSTGRES_USER="store_manager",
        POSTGRES_PASSWORD="change_me",
        REDIS_HOST="redis",
        REDIS_PORT=6379,
        REDIS_DB=0,
        LOG_LEVEL="INFO",
    )


@pytest.mark.asyncio
async def test_admin_panel_denies_regular_user() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=999),
        answer=AsyncMock(),
    )
    service = DummyProductService()

    await admin_panel_handler(message, build_settings(), DummyState(), service)

    message.answer.assert_awaited_once_with(formatter.format_no_access_message())
    assert service.calls == []


@pytest.mark.asyncio
async def test_reviews_handler_sends_link_button() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    settings = build_settings()

    await reviews_handler(message, settings)

    message.answer.assert_awaited_once()
    _, kwargs = message.answer.await_args
    assert kwargs["parse_mode"] == "HTML"
    assert kwargs["reply_markup"].inline_keyboard[0][0].url == settings.reviews_url


@pytest.mark.asyncio
async def test_empty_archive_replaces_navigation_message() -> None:
    message = SimpleNamespace(
        text="Vape bazar Admin",
        edit_text=AsyncMock(),
        delete=AsyncMock(),
        answer=AsyncMock(),
    )
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        data="admin:archive",
        answer=AsyncMock(),
        message=message,
    )
    product_service = SimpleNamespace(
        list_archived_products=AsyncMock(
            return_value=SimpleNamespace(items=[], page=1, total_pages=1),
        )
    )

    await archive_callback_handler(callback, build_settings(), product_service)

    message.edit_text.assert_awaited_once()
    assert message.edit_text.await_args.args[0] == "Архив товаров пуст."
    message.answer.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "publish_to_channel"),
    [("publish", True), ("save_bot_only", False)],
)
async def test_publish_product_handler_routes_preview_action(action: str, publish_to_channel: bool) -> None:
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock()),
    )
    callback_data = AdminPreviewActionCallback(action=action)
    state = ProductDraftState()
    product_service = SimpleNamespace(publish_product=AsyncMock())

    await publish_product_handler(
        callback,
        callback_data,
        state,
        build_settings(),
        product_service,
    )

    product_service.publish_product.assert_awaited_once()
    assert product_service.publish_product.await_args.kwargs["publish_to_channel"] is publish_to_channel
    assert state.cleared is True
    callback.answer.assert_awaited_once()
