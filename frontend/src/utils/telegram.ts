export function getTelegramWebApp() {
  return window.Telegram?.WebApp;
}

export function initializeTelegramWebApp() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return;
  }
  webApp.ready();
  webApp.expand();
  if (webApp.isVersionAtLeast?.("6.1")) {
    webApp.setHeaderColor?.("#140a1f");
    webApp.setBackgroundColor?.("#120916");
  }
  if (webApp.isVersionAtLeast?.("7.7")) {
    webApp.disableVerticalSwipes?.();
  }
}

export function getTelegramUser() {
  const webApp = getTelegramWebApp();
  const unsafeUser = webApp?.initDataUnsafe?.user;
  if (unsafeUser) {
    return unsafeUser;
  }
  if (!webApp?.initData) {
    return null;
  }
  try {
    const userJson = new URLSearchParams(webApp.initData).get("user");
    return userJson ? JSON.parse(userJson) : null;
  } catch {
    return null;
  }
}

export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}

export function getTelegramUsername(): string {
  const username = getTelegramUser()?.username?.trim();
  return username ? `@${username.replace(/^@/, "")}` : "";
}

export function closeTelegramWebApp(): void {
  getTelegramWebApp()?.close?.();
}
