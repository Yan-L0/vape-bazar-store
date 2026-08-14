/// <reference types="vite/client" />

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: {
    user?: {
      id: number;
      first_name?: string;
      username?: string;
      last_name?: string;
    };
  };
  ready: () => void;
  expand: () => void;
        isVersionAtLeast?: (version: string) => boolean;
  onEvent?: (eventType: string, handler: () => void) => void;
  offEvent?: (eventType: string, handler: () => void) => void;
  close?: () => void;
  setHeaderColor?: (color: string) => void;
  setBackgroundColor?: (color: string) => void;
  enableClosingConfirmation?: () => void;
  disableVerticalSwipes?: () => void;
  colorScheme?: "light" | "dark";
}

interface TelegramGlobal {
  WebApp: TelegramWebApp;
}

interface Window {
  Telegram?: TelegramGlobal;
}
