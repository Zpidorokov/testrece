"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type TelegramWindow = Window & {
  Telegram?: {
    WebApp?: {
      initData?: string;
      initDataUnsafe?: {
        user?: {
          id?: number;
        };
      };
      ready?: () => void;
      expand?: () => void;
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
    telegram?.ready?.();
    telegram?.expand?.();
    const initData = telegram?.initData;
    const telegramUserId = telegram?.initDataUnsafe?.user?.id;
    if (!initData || !telegramUserId) {
      return;
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
        setMessage(payload?.detail ?? payload?.message ?? "Не удалось авторизовать Telegram Web App.");
        return;
      }

      startTransition(() => {
        router.refresh();
      });
    })();
  }, [router]);

  if (!message) {
    return null;
  }

  return <div className="auth-banner">{message}</div>;
}

