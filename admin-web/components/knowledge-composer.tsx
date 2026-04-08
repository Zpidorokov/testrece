"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

export function KnowledgeComposer() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("faq");

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind,
          title,
          content,
          metadata_json: {},
          is_active: true,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
        throw new Error(payload?.detail ?? payload?.message ?? "Не удалось сохранить блок знаний");
      }
      setTitle("");
      setContent("");
      startTransition(() => router.refresh());
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-grid">
      <select className="input" value={kind} onChange={(event) => setKind(event.target.value)}>
        <option value="faq">FAQ и общие факты</option>
        <option value="service_info">Услуги</option>
        <option value="promo">Акции</option>
        <option value="policy">Правила</option>
        <option value="contraindication">Ограничения</option>
        <option value="tone_of_voice">Тон общения</option>
        <option value="objection_handling">Работа с возражениями</option>
        <option value="escalation_rule">Когда звать человека</option>
      </select>
      <input className="input" placeholder="Название блока" value={title} onChange={(event) => setTitle(event.target.value)} />
      <textarea
        className="textarea"
        placeholder="Пиши фактами и по делу: это внутренняя опора для AI, а не готовая простыня ответа клиенту."
        rows={6}
        value={content}
        onChange={(event) => setContent(event.target.value)}
      />
      <button className="button" disabled={busy || !title || !content} onClick={() => void submit()}>
        Добавить блок
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}
