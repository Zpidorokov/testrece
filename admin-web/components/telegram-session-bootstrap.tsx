"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

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
      ready?: () => void;
      expand?: () => void;
      requestFullscreen?: () => void;
      disableVerticalSwipes?: () => void;
      enableClosingConfirmation?: () => void;
      setHeaderColor?: (color: string) => void;
      setBackgroundColor?: (color: string) => void;
      setBottomBarColor?: (color: string) => void;
      onEvent?: (eventType: string, handler: (payload?: unknown) => void) => void;
      offEvent?: (eventType: string, handler: (payload?: unknown) => void) => void;
      viewportHeight?: number;
      isExpanded?: boolean;
    };
  };
};

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

    const telegram = (window as TelegramWindow).Telegram?.WebApp;
    const root = document.documentElement;
    telegram?.ready?.();
    telegram?.expand?.();
    telegram?.disableVerticalSwipes?.();
    telegram?.enableClosingConfirmation?.();
    telegram?.setHeaderColor?.("bg_color");
    telegram?.setBackgroundColor?.("bg_color");
    telegram?.setBottomBarColor?.("bg_color");
    const syncViewport = () => {
      const height = telegram?.viewportHeight ? `${telegram.viewportHeight}px` : `${window.innerHeight}px`;
      root.style.setProperty("--app-height", height);
      document.body.style.minHeight = height;
    };
    syncViewport();

    const handleFullscreenFailed = () => {
      root.dataset.fullscreenFailed = "true";
    };

    telegram?.onEvent?.("viewportChanged", syncViewport);
    telegram?.onEvent?.("fullscreenChanged", syncViewport);
    telegram?.onEvent?.("fullscreenFailed", handleFullscreenFailed);

    window.setTimeout(() => {
      telegram?.expand?.();
      telegram?.requestFullscreen?.();
      syncViewport();
    }, 120);

    root.dataset.telegramMiniApp = telegram ? "true" : "false";
    const initData = telegram?.initData;
    const telegramUserId = telegram?.initDataUnsafe?.user?.id;
    if (!initData || !telegramUserId) {
      return () => {
        telegram?.offEvent?.("viewportChanged", syncViewport);
        telegram?.offEvent?.("fullscreenChanged", syncViewport);
        telegram?.offEvent?.("fullscreenFailed", handleFullscreenFailed);
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

      startTransition(() => {
        router.refresh();
      });
    })();

    return () => {
      telegram?.offEvent?.("viewportChanged", syncViewport);
      telegram?.offEvent?.("fullscreenChanged", syncViewport);
      telegram?.offEvent?.("fullscreenFailed", handleFullscreenFailed);
    };
  }, [router]);

  if (!message) {
    return null;
  }

  return <div className="auth-banner">{message}</div>;
}
