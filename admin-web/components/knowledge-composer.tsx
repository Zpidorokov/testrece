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
        throw new Error(payload?.detail ?? payload?.message ?? "Не удалось сохранить knowledge item");
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
        <option value="faq">FAQ</option>
        <option value="service_info">Service info</option>
        <option value="promo">Promo</option>
        <option value="policy">Policy</option>
        <option value="contraindication">Contraindication</option>
        <option value="tone_of_voice">Tone of voice</option>
        <option value="escalation_rule">Escalation rule</option>
      </select>
      <input className="input" placeholder="Заголовок" value={title} onChange={(event) => setTitle(event.target.value)} />
      <textarea className="textarea" placeholder="Контент" rows={6} value={content} onChange={(event) => setContent(event.target.value)} />
      <button className="button" disabled={busy || !title || !content} onClick={() => void submit()}>
        Добавить элемент
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}

