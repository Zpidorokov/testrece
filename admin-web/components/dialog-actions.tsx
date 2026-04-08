"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  dialogId: number;
  mode: string;
};

export function DialogActions({ dialogId, mode }: Props) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function call(path: string, body?: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
        throw new Error(payload?.detail ?? payload?.message ?? "Action failed");
      }
      startTransition(() => router.refresh());
      setText("");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="action-stack">
      <div className="action-row">
        {mode === "manual" ? (
          <button className="button button-secondary" disabled={busy} onClick={() => void call(`/api/dialogs/${dialogId}/return-to-auto`)}>
            Вернуть AI
          </button>
        ) : (
          <button
            className="button button-warning"
            disabled={busy}
            onClick={() => void call(`/api/dialogs/${dialogId}/takeover`, { assigned_user_id: 1, reason: "manual_review" })}
          >
            Take over
          </button>
        )}
      </div>
      <textarea
        className="textarea"
        placeholder="Написать клиенту вручную"
        rows={4}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <button
        className="button"
        disabled={busy || text.trim().length === 0}
        onClick={() => void call(`/api/dialogs/${dialogId}/send-message`, { text, split_mode: "single" })}
      >
        Отправить
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}

