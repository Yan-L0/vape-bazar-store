import { closeTelegramWebApp } from "../utils/telegram";

interface AgeGateProps {
  denied: boolean;
  onAllow: () => void;
  onDeny: () => void;
}

export function AgeGate({ denied, onAllow, onDeny }: AgeGateProps) {
  return (
    <div className="age-gate" role="dialog" aria-modal="true" aria-labelledby="age-gate-title">
      <div className="age-gate__panel">
        <div className="age-gate__mark">18+</div>
        <p className="age-gate__eyebrow">Vape bazar · возрастное ограничение</p>
        <h1 id="age-gate-title">{denied ? "Доступ закрыт" : "Вам уже исполнилось 18 лет?"}</h1>
        <p>
          {denied
            ? "Каталог предназначен только для совершеннолетних пользователей."
            : "Подтвердите совершеннолетие, чтобы перейти в каталог электронных сигарет и жидкостей."}
        </p>

        {denied ? (
          <button className="age-gate__button age-gate__button--secondary" type="button" onClick={closeTelegramWebApp}>
            Закрыть магазин
          </button>
        ) : (
          <div className="age-gate__actions">
            <button className="age-gate__button age-gate__button--primary" type="button" onClick={onAllow}>
              Да, мне есть 18
            </button>
            <button className="age-gate__button age-gate__button--secondary" type="button" onClick={onDeny}>
              Нет
            </button>
          </div>
        )}

        <small>Никотин вызывает зависимость. Продажа несовершеннолетним запрещена.</small>
      </div>
    </div>
  );
}
