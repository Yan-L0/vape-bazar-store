from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"


class ProductCategory(str, enum.Enum):
    POD_SYSTEMS = "POD_SYSTEMS"
    LIQUIDS = "LIQUIDS"
    CARTRIDGES_COILS = "CARTRIDGES_COILS"
    SNUS_PLATES = "SNUS_PLATES"
    DISPOSABLES = "DISPOSABLES"

    @property
    def label(self) -> str:
        return {
            ProductCategory.POD_SYSTEMS: "POD-системы",
            ProductCategory.LIQUIDS: "Жидкости",
            ProductCategory.CARTRIDGES_COILS: "Картриджи и испарители",
            ProductCategory.SNUS_PLATES: "Снюс и пластинки",
            ProductCategory.DISPOSABLES: "Одноразовые электронные устройства",
        }[self]

    @classmethod
    def from_label(cls, label: str) -> "ProductCategory":
        normalized = label.strip().lower()
        mapping = {
            "pod-системы": cls.POD_SYSTEMS,
            "под-системы": cls.POD_SYSTEMS,
            "pod системы": cls.POD_SYSTEMS,
            "жидкости": cls.LIQUIDS,
            "картриджи и испарители": cls.CARTRIDGES_COILS,
            "картриджы и испарители": cls.CARTRIDGES_COILS,
            "снюс и пластинки": cls.SNUS_PLATES,
            "одноразовые электронные устройства": cls.DISPOSABLES,
            "одноразовые устройства": cls.DISPOSABLES,
            "одноразки": cls.DISPOSABLES,
        }
        return mapping[normalized]


class ProductSource(str, enum.Enum):
    BOT = "BOT"
    CHANNEL_IMPORT = "CHANNEL_IMPORT"


class OrderContactMethod(str, enum.Enum):
    TELEGRAM = "TELEGRAM"
    PHONE = "PHONE"
    WHATSAPP = "WHATSAPP"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    KEPT = "KEPT"
    PURCHASED = "PURCHASED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category"),
        nullable=False,
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    old_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        default=ProductStatus.ACTIVE,
        server_default=ProductStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_media_group_message_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger),
        nullable=True,
    )
    source: Mapped[ProductSource] = mapped_column(
        Enum(ProductSource, name="product_source"),
        default=ProductSource.BOT,
        server_default=ProductSource.BOT.value,
        nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    caption_entities_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    html_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    photos: Mapped[list["ProductPhoto"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductPhoto.sort_order",
    )
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")


class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    product: Mapped[Product] = relationship(back_populates="photos")


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_username: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_method: Mapped[OrderContactMethod] = mapped_column(
        Enum(OrderContactMethod, name="order_contact_method"),
        nullable=False,
    )
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship(back_populates="order_items")
