import type { StoreMeta } from "../types";

interface HeaderBannerProps {
  meta: StoreMeta | null;
  favoritesCount: number;
  onOpenFavorites: () => void;
}

export function HeaderBanner({ meta, favoritesCount, onOpenFavorites }: HeaderBannerProps) {
  const shopName = meta?.shop_name || "Vape bazar";

  return (
    <header className="store-header">
      <div className="store-header__brand">
        <h1>{shopName}</h1>
        <span>18+</span>
      </div>
      <button className="icon-button" type="button" onClick={onOpenFavorites} aria-label="Открыть избранное">
        <span>♡</span>
        {favoritesCount > 0 ? <span className="icon-badge">{favoritesCount}</span> : null}
      </button>
    </header>
  );
}
