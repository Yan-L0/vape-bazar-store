import { useEffect, useState } from "react";

import type { Product } from "../types";
import { formatPrice } from "../utils/format";

interface ProductModalProps {
  product: Product;
  supportUrl: string;
  isFavorite: boolean;
  inCart: boolean;
  onClose: () => void;
  onToggleFavorite: () => void;
  onAddToCart: () => void;
}

export function ProductModal({
  product,
  supportUrl,
  isFavorite,
  inCart,
  onClose,
  onToggleFavorite,
  onAddToCart,
}: ProductModalProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const photos = product.photos.length ? product.photos : [""];

  useEffect(() => {
    const scrollY = window.scrollY;
    const previousStyles = {
      position: document.body.style.position,
      top: document.body.style.top,
      width: document.body.style.width,
      overflow: document.body.style.overflow,
    };

    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = "100%";
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.position = previousStyles.position;
      document.body.style.top = previousStyles.top;
      document.body.style.width = previousStyles.width;
      document.body.style.overflow = previousStyles.overflow;
      window.scrollTo(0, scrollY);
    };
  }, []);

  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <div className="sheet sheet--product">
        <div className="sheet__header">
          <button className="text-button" type="button" onClick={onClose}>
            Назад
          </button>
          <button className="icon-button" type="button" onClick={onToggleFavorite} aria-label="Избранное">
            {isFavorite ? "♥" : "♡"}
          </button>
        </div>

        <div className="product-modal__gallery">
          {photos[currentIndex] ? (
            <img
              key={`${photos[currentIndex]}-${currentIndex}`}
              className="product-modal__image"
              src={photos[currentIndex]}
              alt={product.title}
            />
          ) : (
            <div className="product-card__placeholder product-modal__placeholder">STORE</div>
          )}

          {photos.length > 1 ? (
            <>
              <button
                className="carousel-button carousel-button--prev"
                type="button"
                onClick={() => setCurrentIndex((currentIndex - 1 + photos.length) % photos.length)}
                aria-label="Предыдущее фото"
              >
                ‹
              </button>
              <button
                className="carousel-button carousel-button--next"
                type="button"
                onClick={() => setCurrentIndex((currentIndex + 1) % photos.length)}
                aria-label="Следующее фото"
              >
                ›
              </button>
              <div className="carousel-indicator">
                {currentIndex + 1} / {photos.length}
              </div>
            </>
          ) : null}
        </div>

        {photos.length > 1 ? (
          <div className="product-modal__thumbs">
            {photos.map((photo, index) => (
              <button
                key={`${photo}-${index}`}
                className={`product-modal__thumb ${index === currentIndex ? "product-modal__thumb--active" : ""}`}
                type="button"
                onClick={() => setCurrentIndex(index)}
                aria-label={`Фото ${index + 1}`}
              >
                <img src={photo} alt={`${product.title} ${index + 1}`} />
              </button>
            ))}
          </div>
        ) : null}

        <div className="product-modal__content">
          <div className="product-modal__status-row">
            <div className="product-modal__status">{product.status_label}</div>
            <div className="product-modal__stock">Осталось {product.stock_quantity} шт.</div>
          </div>
          <h2 className="product-modal__title">{product.title}</h2>
          <div className="product-modal__price">
            {product.old_price ? <span className="price-old">{formatPrice(product.old_price)}</span> : null}
            <strong>{formatPrice(product.price)}</strong>
          </div>

          <dl className="product-modal__details">
            <div className="product-modal__detail">
              <dt>Характеристика</dt>
              <dd>{product.size}</dd>
            </div>
            <div className="product-modal__detail">
              <dt>Состояние</dt>
              <dd>{product.condition}</dd>
            </div>
            <div className="product-modal__detail">
              <dt>Категория</dt>
              <dd>{product.category_label}</dd>
            </div>
          </dl>

          <div className="product-modal__description">
            <span>Описание</span>
            <p>{product.description || "Менеджер добавит подробности по запросу."}</p>
          </div>

          <div className="product-modal__actions">
            <button className="primary-button" type="button" onClick={onAddToCart} disabled={product.status === "SOLD"}>
              {product.status === "SOLD" ? "Продано" : inCart ? "Уже в корзине" : "Добавить в корзину"}
            </button>
            <a className="secondary-button" href={supportUrl} target="_blank" rel="noreferrer">
              Написать менеджеру
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
