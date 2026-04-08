"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type Insets = {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
};

type TelegramWindow = Window & {
  Telegram?: {
    WebApp?: {
      version?: string;
      initData?: string;
      initDataUnsafe?: {
        user?: {
          id?: number;
        };
      };
      themeParams?: Record<string, string>;
      safeAreaInset?: Insets;
      contentSafeAreaInset?: Insets;
      viewportHeight?: number;
      isExpanded?: boolean;
      isFullscreen?: boolean;
      ready?: () => void;
      expand?: () => void;
      requestFullscreen?: () => void;
      disableVerticalSwipes?: () => void;
      enableClosingConfirmation?: () => void;
      setHeaderColor?: (color: string) => void;
      setBackgroundColor?: (color: string) => void;
      setBottomBarColor?: (color: string) => void;
      onEvent?: (eventType: string, handler: () => void) => void;
      offEvent?: (eventType: string, handler: () => void) => void;
    };
  };
};

function applyInsets(root: HTMLElement, prefix: string, insets?: Insets) {
  root.style.setProperty(`${prefix}-top`, `${insets?.top ?? 0}px`);
  root.style.setProperty(`${prefix}-right`, `${insets?.right ?? 0}px`);
  root.style.setProperty(`${prefix}-bottom`, `${insets?.bottom ?? 0}px`);
  root.style.setProperty(`${prefix}-left`, `${insets?.left ?? 0}px`);
}

export function TelegramSessionBootstrap() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const bootstrappedRef = useRef(false);
  const [, startTransition] = useTransition();

  useEffect(() => {
    if (bootstrappedRef.current) {
      return;
    }
    bootstrappedRef.current = true;

    const root = document.documentElement;
    const telegram = (window as TelegramWindow).Telegram?.WebApp;
    const sessionCacheKey = "botreceptionist:session:init";

    const syncViewport = () => {
      const height = telegram?.viewportHeight ? `${telegram.viewportHeight}px` : `${window.innerHeight}px`;
      root.style.setProperty("--app-height", height);
      root.dataset.telegramFullscreen = telegram?.isFullscreen ? "true" : "false";
    };

    const syncInsets = () => {
      applyInsets(root, "--tg-safe-area-inset", telegram?.safeAreaInset);
      applyInsets(root, "--tg-content-safe-area-inset", telegram?.contentSafeAreaInset ?? telegram?.safeAreaInset);
    };

    const syncAll = () => {
      syncViewport();
      syncInsets();
    };

    telegram?.ready?.();
    telegram?.expand?.();
    telegram?.disableVerticalSwipes?.();
    telegram?.enableClosingConfirmation?.();
    telegram?.setHeaderColor?.("bg_color");
    telegram?.setBackgroundColor?.("bg_color");
    telegram?.setBottomBarColor?.("bg_color");
    syncAll();

    const handleFullscreenFailed = () => {
      root.dataset.fullscreenFailed = "true";
    };

    telegram?.onEvent?.("viewportChanged", syncAll);
    telegram?.onEvent?.("fullscreenChanged", syncAll);
    telegram?.onEvent?.("fullscreenFailed", handleFullscreenFailed);
    telegram?.onEvent?.("safeAreaChanged", syncInsets);
    telegram?.onEvent?.("contentSafeAreaChanged", syncInsets);

    window.setTimeout(() => {
      telegram?.expand?.();
      if (!telegram?.isFullscreen) {
        telegram?.requestFullscreen?.();
      }
      syncAll();
    }, 120);

    root.dataset.telegramMiniApp = telegram ? "true" : "false";

    const initData = telegram?.initData;
    const telegramUserId = telegram?.initDataUnsafe?.user?.id;
    if (!initData || !telegramUserId) {
      return () => {
        telegram?.offEvent?.("viewportChanged", syncAll);
        telegram?.offEvent?.("fullscreenChanged", syncAll);
        telegram?.offEvent?.("fullscreenFailed", handleFullscreenFailed);
        telegram?.offEvent?.("safeAreaChanged", syncInsets);
        telegram?.offEvent?.("contentSafeAreaChanged", syncInsets);
      };
    }

    if (sessionStorage.getItem(sessionCacheKey) === initData) {
      return () => {
        telegram?.offEvent?.("viewportChanged", syncAll);
        telegram?.offEvent?.("fullscreenChanged", syncAll);
        telegram?.offEvent?.("fullscreenFailed", handleFullscreenFailed);
        telegram?.offEvent?.("safeAreaChanged", syncInsets);
        telegram?.offEvent?.("contentSafeAreaChanged", syncInsets);
      };
    }

    void (async () => {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          telegram_user_id: telegramUserId,
          init_data: initData,
        }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
        setMessage(payload?.detail ?? payload?.message ?? "Не удалось открыть рабочую панель.");
        return;
      }

      sessionStorage.setItem(sessionCacheKey, initData);
      startTransition(() => {
        router.refresh();
      });
    })();

    return () => {
      telegram?.offEvent?.("viewportChanged", syncAll);
      telegram?.offEvent?.("fullscreenChanged", syncAll);
      telegram?.offEvent?.("fullscreenFailed", handleFullscreenFailed);
      telegram?.offEvent?.("safeAreaChanged", syncInsets);
      telegram?.offEvent?.("contentSafeAreaChanged", syncInsets);
    };
  }, [router]);

  if (!message) {
    return null;
  }

  return <div className="auth-banner">{message}</div>;
}
