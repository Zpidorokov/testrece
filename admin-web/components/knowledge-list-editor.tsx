"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import type { KnowledgeItem } from "@/lib/types";
import { formatKnowledgeKind } from "@/lib/ui";

const kindOptions = [
  { value: "faq", label: "FAQ и общие факты" },
  { value: "service_info", label: "Услуги" },
  { value: "promo", label: "Акции" },
  { value: "policy", label: "Правила" },
  { value: "contraindication", label: "Ограничения" },
  { value: "tone_of_voice", label: "Тон общения" },
  { value: "objection_handling", label: "Работа с возражениями" },
  { value: "escalation_rule", label: "Когда звать человека" },
];

export function KnowledgeListEditor({ items }: { items: KnowledgeItem[] }) {
  const groups = items.reduce(
    (accumulator, item) => {
      const key = item.kind;
      accumulator[key] = accumulator[key] ? [...accumulator[key], item] : [item];
      return accumulator;
    },
    {} as Record<string, KnowledgeItem[]>,
  );

  return (
    <div className="knowledge-groups">
      {Object.entries(groups).map(([kind, group]) => (
        <section className="knowledge-group" key={kind}>
          <div className="knowledge-group-head">
            <strong>{formatKnowledgeKind(kind)}</strong>
            <span>{group.length}</span>
          </div>
          <div className="stack">
            {group.map((item) => (
              <KnowledgeEditorCard item={item} key={item.id} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function KnowledgeEditorCard({ item }: { item: KnowledgeItem }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    kind: item.kind,
    title: item.title,
    content: item.content,
    is_active: item.is_active,
  });

  async function mutate(method: "PATCH" | "DELETE", body?: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/knowledge/${item.id}`, {
        method,
        headers: body
          ? {
              "Content-Type": "application/json",
            }
          : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
        throw new Error(payload?.detail ?? payload?.message ?? "Не удалось сохранить изменения");
      }
      startTransition(() => router.refresh());
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="panel knowledge-card">
      <div className="knowledge-card-head">
        <div>
          <div className="mono knowledge-id">#{item.id}</div>
          <strong>{formatKnowledgeKind(draft.kind)}</strong>
        </div>
        <label className="switch-row">
          <input
            checked={draft.is_active}
            onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))}
            type="checkbox"
          />
          <span>{draft.is_active ? "Активно" : "Выключено"}</span>
        </label>
      </div>

      <div className="form-grid">
        <select className="input" value={draft.kind} onChange={(event) => setDraft((current) => ({ ...current, kind: event.target.value }))}>
          {kindOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          className="input"
          placeholder="Название блока"
          value={draft.title}
          onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
        />
        <textarea
          className="textarea"
          placeholder="Текст, который AI может использовать как внутренний факт"
          rows={6}
          value={draft.content}
          onChange={(event) => setDraft((current) => ({ ...current, content: event.target.value }))}
        />
      </div>

      <div className="action-row">
        <button
          className="button"
          disabled={busy || !draft.title.trim() || !draft.content.trim()}
          onClick={() =>
            void mutate("PATCH", {
              kind: draft.kind,
              title: draft.title.trim(),
              content: draft.content.trim(),
              is_active: draft.is_active,
            })
          }
        >
          Сохранить
        </button>
        <button className="button button-secondary" disabled={busy} onClick={() => setDraft({ kind: item.kind, title: item.title, content: item.content, is_active: item.is_active })}>
          Сбросить
        </button>
        <button className="button button-danger" disabled={busy} onClick={() => void mutate("DELETE")}>
          Удалить
        </button>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
    </article>
  );
}
