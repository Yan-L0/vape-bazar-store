from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.database.models import Product, ProductCategory, ProductStatus
from app.web.schemas import CategoryResponse, ProductResponse


_CATEGORY_LABELS = {
    ProductCategory.POD_SYSTEMS: "POD-системы",
    ProductCategory.LIQUIDS: "Жидкости",
    ProductCategory.CARTRIDGES_COILS: "Картриджи и испарители",
    ProductCategory.SNUS_PLATES: "Снюс и пластинки",
    ProductCategory.DISPOSABLES: "Одноразовые электронные устройства",
}

_STATUS_LABELS = {
    ProductStatus.ACTIVE: "В наличии",
    ProductStatus.SOLD: "Продано",
}


def category_response(category: ProductCategory) -> CategoryResponse:
    return CategoryResponse(key=category, label=_CATEGORY_LABELS[category])


def product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        title=product.title,
        price=product.price,
        old_price=product.old_price,
        stock_quantity=product.stock_quantity,
        category=product.category,
        category_label=_CATEGORY_LABELS[product.category],
        size=product.size,
        condition=product.condition,
        description=product.description,
        status=product.status,
        status_label=_STATUS_LABELS[product.status],
        photos=[f"/api/media/{photo.id}" for photo in product.photos],
        photo_count=len(product.photos),
        created_at=product.created_at,
        is_new=_is_new_product(product),
    )


def _is_new_product(product: Product) -> bool:
    condition = product.condition.lower()
    if "нов" in condition or "new" in condition:
        return True
    if not product.created_at:
        return False
    return product.created_at >= datetime.now(tz=UTC) - timedelta(days=14)
