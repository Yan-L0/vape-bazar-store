import { useEffect, useState } from "react";

interface CheckoutSheetProps {
  loading: boolean;
  error: string | null;
  initialUsername?: string;
  onClose: () => void;
  onSubmit: (payload: {
    username: string;
    phone: string;
  }) => Promise<void>;
}

export function CheckoutSheet({
  loading,
  error,
  initialUsername,
  onClose,
  onSubmit,
}: CheckoutSheetProps) {
  const [username, setUsername] = useState(initialUsername || "");
  const [phone, setPhone] = useState("");
  const [viewport, setViewport] = useState<{ height?: number; top?: number }>({});

  useEffect(() => {
    if (!username.trim() && initialUsername) {
      setUsername(initialUsername);
    }
  }, [initialUsername, username]);

  useEffect(() => {
    const visualViewport = window.visualViewport;
    if (!visualViewport) {
      return;
    }
    const syncViewport = () => {
      setViewport({ height: visualViewport.height, top: visualViewport.offsetTop });
    };
    syncViewport();
    visualViewport.addEventListener("resize", syncViewport);
    visualViewport.addEventListener("scroll", syncViewport);
    return () => {
      visualViewport.removeEventListener("resize", syncViewport);
      visualViewport.removeEventListener("scroll", syncViewport);
    };
  }, []);

  return (
    <div
      className="overlay overlay--checkout"
      role="dialog"
      aria-modal="true"
      style={{ height: viewport.height, top: viewport.top }}
    >
      <div className="sheet sheet--checkout">
        <div className="sheet__header">
          <h2>Оформление заказа</h2>
          <button className="text-button" type="button" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <form
          className="checkout-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSubmit({ username, phone });
          }}
        >
          <label>
            Username в Telegram
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Введите username"
              autoCapitalize="none"
              autoCorrect="off"
              autoComplete="username"
              required
            />
            <small className="field-hint">
              Username подставлен из вашего Telegram. При необходимости его можно изменить.
            </small>
          </label>

          <label>
            Телефон для связи
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+7 900 000-00-00"
              inputMode="tel"
              autoComplete="tel"
            />
            <small className="field-hint">Необязательно. Можно оставить пустым, если удобнее общаться только в Telegram.</small>
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button className="checkout-button checkout-button--success" type="submit" disabled={loading}>
            {loading ? "Создаём заказ..." : "Подтвердить заказ"}
          </button>
        </form>
      </div>
    </div>
  );
}
