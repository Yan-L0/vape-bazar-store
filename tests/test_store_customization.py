from pathlib import Path

from app.database.models import OrderContactMethod, ProductCategory
from app.keyboards.admin import category_inline_keyboard, description_inline_keyboard, import_category_keyboard
from app.keyboards.catalog import catalog_categories_keyboard
from app.web.schemas import OrderCreateRequest


def test_store_exposes_all_shop_categories() -> None:
    assert [(category.value, category.label) for category in ProductCategory] == [
        ("POD_SYSTEMS", "POD-системы"),
        ("LIQUIDS", "Жидкости"),
        ("CARTRIDGES_COILS", "Картриджи и испарители"),
        ("SNUS_PLATES", "Снюс и пластинки"),
        ("DISPOSABLES", "Одноразовые электронные устройства"),
    ]


def test_mobile_category_list_scrolls_without_cramping_long_labels() -> None:
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")

    assert "grid-auto-flow: column" in styles
    assert "grid-auto-columns: minmax(156px, 64vw)" in styles
    assert "overflow-x: auto" in styles


def test_all_categories_are_available_in_bot_and_admin_keyboards() -> None:
    expected_labels = [category.label for category in ProductCategory]
    catalog_labels = [row[0].text for row in catalog_categories_keyboard().inline_keyboard]
    add_labels = [row[0].text for row in category_inline_keyboard().inline_keyboard]
    import_labels = [row[0].text for row in import_category_keyboard().inline_keyboard]

    assert catalog_labels == expected_labels + ["Назад"]
    assert add_labels == expected_labels
    assert import_labels == expected_labels


def test_vape_bazar_brand_is_used_across_user_facing_surfaces() -> None:
    paths = [
        Path("app/services/formatter.py"),
        Path("app/web/main.py"),
        Path("frontend/index.html"),
        Path("frontend/src/components/AgeGate.tsx"),
        Path("frontend/src/components/HeaderBanner.tsx"),
        Path("frontend/src/pages/StorePage.tsx"),
        Path("README.md"),
    ]

    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "FOGPOINT" not in source
        assert "Vape bazar" in source


def test_checkout_accepts_payload_without_name_or_comment() -> None:
    payload = OrderCreateRequest.model_validate(
        {
            "username": "@buyer",
            "phone": None,
            "contact_method": OrderContactMethod.TELEGRAM,
            "items": [{"product_id": 1, "quantity": 1}],
        }
    )

    assert payload.name is None
    assert payload.comment is None


def test_description_step_has_zero_skip_button() -> None:
    button = description_inline_keyboard().inline_keyboard[0][0]

    assert button.text == "0"
    assert "description_skip" in button.callback_data


def test_mini_app_loads_telegram_sdk_before_frontend() -> None:
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "https://telegram.org/js/telegram-web-app.js" in index_html
    assert index_html.index("telegram-web-app.js") < index_html.index("/src/main.tsx")


def test_mini_app_uses_expanded_mode_without_fullscreen() -> None:
    telegram_source = Path("frontend/src/utils/telegram.ts").read_text(encoding="utf-8")

    assert "webApp.expand()" in telegram_source
    assert "requestFullscreen" not in telegram_source


def test_checkout_sheet_stays_bottom_aligned_and_motion_is_accessible() -> None:
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")

    assert ".overlay--checkout" in styles
    assert "align-items: flex-end" in styles
    assert "@keyframes product-card-in" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


def test_product_modal_is_compact_and_keeps_full_photo_visible() -> None:
    store_source = Path("frontend/src/pages/StorePage.tsx").read_text(encoding="utf-8")
    modal_source = Path("frontend/src/components/ProductModal.tsx").read_text(encoding="utf-8")
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")

    assert "welcome-note" not in store_source
    assert "Привет," not in store_source
    assert "product-modal__status-row" in modal_source
    assert "product-modal__description" in modal_source
    assert "product-modal__detail--description" not in modal_source
    assert ".product-modal__image" in styles
    assert "object-fit: contain" in styles
    assert "width: 100%" in styles
    assert "height: auto" in styles
    assert "max-height: none" in styles
    assert ".sheet--product > .product-modal__gallery" in styles
    assert "flex: 0 0 auto" in styles
    assert "@keyframes product-image-in" in styles
    assert "font-size: clamp(21px, 5vw, 28px)" in styles
    assert ".product-modal__description" in styles
    assert "text-align: left" in styles
