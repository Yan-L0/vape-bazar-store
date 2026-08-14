import { useEffect, useMemo, useState } from "react";

import { createOrder, fetchCategories, fetchMeta, fetchProducts, validateWebApp } from "../api/client";
import { CartDrawer } from "../components/CartDrawer";
import { AgeGate } from "../components/AgeGate";
import { CheckoutSheet } from "../components/CheckoutSheet";
import { FavoritesDrawer } from "../components/FavoritesDrawer";
import { HeaderBanner } from "../components/HeaderBanner";
import { ProductCard } from "../components/ProductCard";
import { ProductModal } from "../components/ProductModal";
import { useCartStore } from "../store/cart";
import { useFavoritesStore } from "../store/favorites";
import type { Category, Product, StoreMeta, WebAppUser } from "../types";
import { getInitData, getTelegramUser, getTelegramUsername, getTelegramWebApp, initializeTelegramWebApp } from "../utils/telegram";

type SortMode = "default" | "cheap" | "expensive" | "new" | "discount";

const categoryVisuals: Record<string, { title: string; subtitle: string }> = {
  POD_SYSTEMS: { title: "POD-системы", subtitle: "Многоразовые устройства" },
  LIQUIDS: { title: "Жидкости", subtitle: "Вкусы, объёмы и крепость" },
  CARTRIDGES_COILS: { title: "Картриджи и испарители", subtitle: "Расходники для устройств" },
  SNUS_PLATES: { title: "Снюс и пластинки", subtitle: "Никотиновая продукция" },
  DISPOSABLES: { title: "Одноразовые электронные устройства", subtitle: "Готовые устройства" },
};

type AgeGateState = "pending" | "allowed" | "denied";
const AGE_GATE_STORAGE_KEY = "vape-bazar-age-confirmed";

const sortOptions: Array<{ value: SortMode; label: string }> = [
  { value: "default", label: "По умолчанию" },
  { value: "cheap", label: "Сначала дешевле" },
  { value: "expensive", label: "Сначала дороже" },
  { value: "new", label: "Новые" },
  { value: "discount", label: "Со скидкой" },
];

export function StorePage() {
  const [meta, setMeta] = useState<StoreMeta | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [sortMode, setSortMode] = useState<SortMode>("default");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [showCart, setShowCart] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [showFavorites, setShowFavorites] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [webAppUser, setWebAppUser] = useState<WebAppUser | null>(() => getTelegramUser());
  const [ageGate, setAgeGate] = useState<AgeGateState>(() =>
    sessionStorage.getItem(AGE_GATE_STORAGE_KEY) === "yes" ? "allowed" : "pending",
  );

  const cartItems = useCartStore((state) => state.items);
  const addItem = useCartStore((state) => state.addItem);
  const increment = useCartStore((state) => state.increment);
  const decrement = useCartStore((state) => state.decrement);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);
  const pruneCart = useCartStore((state) => state.pruneUnavailable);

  const favoriteIds = useFavoritesStore((state) => state.ids);
  const toggleFavorite = useFavoritesStore((state) => state.toggle);
  const hasFavorite = useFavoritesStore((state) => state.has);
  const pruneFavorites = useFavoritesStore((state) => state.pruneMissing);

  useEffect(() => {
    initializeTelegramWebApp();
    void loadData();
    void tryValidateTelegram();
  }, []);

  useEffect(() => {
    const refreshCatalog = () => {
      void refreshProducts();
    };
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        refreshCatalog();
      }
    };
    const webApp = getTelegramWebApp();
    const timer = window.setInterval(refreshCatalog, 2000);
    webApp?.onEvent?.("activated", refreshCatalog);
    window.addEventListener("focus", refreshCatalog);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.clearInterval(timer);
      webApp?.offEvent?.("activated", refreshCatalog);
      window.removeEventListener("focus", refreshCatalog);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  useEffect(() => {
    if (loading) {
      return;
    }
    const availableIds = products.map((product) => product.id);
    pruneCart(availableIds);
    pruneFavorites(availableIds);
    if (selectedProduct && !availableIds.includes(selectedProduct.id)) {
      setSelectedProduct(null);
    }
  }, [loading, products, pruneCart, pruneFavorites, selectedProduct]);

  async function loadData() {
    try {
      setLoading(true);
      const [metaData, categoryData, productData] = await Promise.all([fetchMeta(), fetchCategories(), fetchProducts()]);
      setMeta(metaData);
      setCategories(categoryData);
      setProducts(productData);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить каталог.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshProducts() {
    try {
      const productData = await fetchProducts();
      setProducts(productData);
    } catch {
      // Keep the last valid catalog during short network interruptions.
    }
  }

  async function tryValidateTelegram() {
    const initData = getInitData();
    if (!initData) {
      return;
    }
    try {
      const response = await validateWebApp(initData);
      setWebAppUser(response.user);
    } catch {
      setWebAppUser(null);
    }
  }

  const filteredProducts = useMemo(
    () =>
      products
        .filter((product) => {
          if (selectedCategory !== "ALL" && product.category !== selectedCategory) {
            return false;
          }
          if (!search.trim()) {
            return true;
          }
          const needle = search.trim().toLowerCase();
          return [product.title, product.description || "", product.category_label].join(" ").toLowerCase().includes(needle);
        })
        .sort((left, right) => {
          switch (sortMode) {
            case "cheap":
              return left.price - right.price;
            case "expensive":
              return right.price - left.price;
            case "new":
              return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
            case "discount":
              return Number(Boolean(right.old_price)) - Number(Boolean(left.old_price));
            default:
              return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
          }
        }),
    [products, search, selectedCategory, sortMode],
  );

  const activeCategoryLabel =
    selectedCategory === "ALL"
      ? "Все товары"
      : categories.find((category) => category.key === selectedCategory)?.label || "Категория";

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  async function handleCheckoutSubmit(payload: {
    username: string;
    phone: string;
  }) {
    const initData = getInitData();
    setCheckoutLoading(true);
    setCheckoutError(null);
    try {
      const response = await createOrder({
        init_data: initData || null,
        username: payload.username,
        phone: payload.phone.trim() ? payload.phone.trim() : null,
        contact_method: "TELEGRAM",
        items: cartItems.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
        })),
      });
      clearCart();
      setShowCheckout(false);
      setShowCart(false);
      setSuccessMessage(response.message);
    } catch (submitError) {
      setCheckoutError(submitError instanceof Error ? submitError.message : "Не удалось создать заказ.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  if (ageGate !== "allowed") {
    return (
      <AgeGate
        denied={ageGate === "denied"}
        onAllow={() => {
          sessionStorage.setItem(AGE_GATE_STORAGE_KEY, "yes");
          setAgeGate("allowed");
        }}
        onDeny={() => setAgeGate("denied")}
      />
    );
  }

  return (
    <div className="app-shell">
      <div className="page-container">
        <HeaderBanner meta={meta} favoritesCount={favoriteIds.length} onOpenFavorites={() => setShowFavorites(true)} />

        <section className="search-section">
          <label className="search-input">
            <span className="search-input__icon">⌕</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск товаров..." />
          </label>
        </section>

        <section className="category-section">
          <div className="section-heading">
            <h2>Категории</h2>
            <span>{categories.length} раздела</span>
          </div>

          <div className="category-carousel">
            <div className="category-scroller">
              <button
                className={`category-card ${selectedCategory === "ALL" ? "category-card--active" : ""}`}
                type="button"
                onClick={() => setSelectedCategory("ALL")}
              >
                <span>Все товары</span>
                <small>Весь каталог Vape bazar</small>
              </button>
              {categories.map((category) => (
                <button
                  key={category.key}
                  className={`category-card ${selectedCategory === category.key ? "category-card--active" : ""}`}
                  type="button"
                  onClick={() => setSelectedCategory(category.key)}
                >
                  <span>{categoryVisuals[category.key]?.title || category.label}</span>
                  <small>{categoryVisuals[category.key]?.subtitle || category.label}</small>
                </button>
              ))}
            </div>

          </div>
        </section>

        <section className="products-section">
          <div className="products-toolbar">
            <div>
              <h2>{activeCategoryLabel}</h2>
              <span>{filteredProducts.length} товаров</span>
            </div>

            <div className="sort-panel">
              <span className="sort-panel__label">Сортировка</span>
              <div className="sort-chip-row">
                {sortOptions.map((option) => (
                  <button
                    key={option.value}
                    className={`sort-chip ${sortMode === option.value ? "sort-chip--active" : ""}`}
                    type="button"
                    onClick={() => setSortMode(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {error ? <div className="form-error form-error--page">{error}</div> : null}

          {loading ? (
            <div className="products-grid">
              {Array.from({ length: 8 }).map((_, index) => (
                <div className="product-skeleton" key={index} />
              ))}
            </div>
          ) : null}

          {!loading && !filteredProducts.length ? (
            <div className="empty-state">
              <p>Ничего не найдено.</p>
              <span>Попробуйте поменять категорию или уточнить поисковый запрос.</span>
            </div>
          ) : null}

          {!loading && filteredProducts.length ? (
            <div className="products-grid">
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  isFavorite={hasFavorite(product.id)}
                  inCart={cartItems.some((item) => item.productId === product.id)}
                  onOpen={() => setSelectedProduct(product)}
                  onToggleFavorite={() => toggleFavorite(product.id)}
                  onAddToCart={() => {
                    if (product.status === "ACTIVE") {
                      addItem(product.id);
                    }
                  }}
                />
              ))}
            </div>
          ) : null}
        </section>
      </div>

      <button className="cart-fab" type="button" onClick={() => setShowCart(true)}>
        <span>🛒</span>
        {cartCount ? <strong>{cartCount}</strong> : null}
      </button>

      {selectedProduct ? (
        <ProductModal
          key={selectedProduct.id}
          product={selectedProduct}
          supportUrl={meta?.support_url || "#"}
          isFavorite={hasFavorite(selectedProduct.id)}
          inCart={cartItems.some((item) => item.productId === selectedProduct.id)}
          onClose={() => setSelectedProduct(null)}
          onToggleFavorite={() => toggleFavorite(selectedProduct.id)}
          onAddToCart={() => {
            if (selectedProduct.status === "ACTIVE") {
              addItem(selectedProduct.id);
            }
          }}
        />
      ) : null}

      {showCart ? (
        <CartDrawer
          items={cartItems}
          products={products}
          onClose={() => setShowCart(false)}
          onCheckout={() => setShowCheckout(true)}
          onIncrement={(productId) => increment(productId, products.find((product) => product.id === productId)?.stock_quantity || 1)}
          onDecrement={decrement}
          onRemove={removeItem}
        />
      ) : null}

      {showFavorites ? (
        <FavoritesDrawer
          products={products}
          favoriteIds={favoriteIds}
          cartIds={cartItems.map((item) => item.productId)}
          onClose={() => setShowFavorites(false)}
          onOpenProduct={(product) => {
            setShowFavorites(false);
            setSelectedProduct(product);
          }}
          onToggleFavorite={toggleFavorite}
          onAddToCart={(productId) => addItem(productId)}
        />
      ) : null}

      {showCheckout ? (
        <CheckoutSheet
          loading={checkoutLoading}
          error={checkoutError}
          initialUsername={webAppUser?.username ? `@${webAppUser.username}` : getTelegramUsername()}
          onClose={() => setShowCheckout(false)}
          onSubmit={handleCheckoutSubmit}
        />
      ) : null}

      {successMessage ? (
        <div className="overlay" role="dialog" aria-modal="true">
          <div className="sheet sheet--success">
            <div className="success-mark">✓</div>
            <h2>Заказ создан</h2>
            <p>{successMessage}</p>
            <p className="success-subtitle">Админ уже получил уведомление в Telegram.</p>
            <button className="checkout-button checkout-button--success" type="button" onClick={() => setSuccessMessage(null)}>
              Вернуться в каталог
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
