import Link from "next/link";

import { StatusPill } from "@/components/status-pill";
import { getClient } from "@/lib/api";
import { formatClientStatus } from "@/lib/ui";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ClientDetailPage({ params }: Props) {
  const { id } = await params;
  const client = await getClient(id);

  if (!client) {
    return (
      <div className="panel">
        <h3>Клиент не найден</h3>
        <p className="panel-subtitle">Проверьте доступ к API и наличие токена для чтения данных.</p>
      </div>
    );
  }

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Клиент #{client.id}</span>
          <h2>{client.name ?? "Без имени"}</h2>
          <p>Карточка клиента, внутренние заметки и быстрый переход обратно к переписке.</p>
        </div>
        <Link className="button button-ghost" href="/dialogs">
          К диалогам
        </Link>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Основное</h3>
          <div className="stack">
            <div>
              <strong>Статус</strong>
              <div>
                <StatusPill label={formatClientStatus(client.status)} />
              </div>
            </div>
            <div>
              <strong>Telegram ID</strong>
              <div className="mono">{client.telegram_user_id}</div>
            </div>
            <div>
              <strong>Ник в Telegram</strong>
              <div>{client.username ? `@${client.username}` : "—"}</div>
            </div>
            <div>
              <strong>Телефон</strong>
              <div>{client.phone ?? "—"}</div>
            </div>
          </div>
        </article>

        <article className="panel">
          <h3>Теги и заметки</h3>
          <div className="stack">
            <div className="action-row">
              {client.tags.length ? client.tags.map((tag) => <StatusPill key={tag} label={tag} tone="success" />) : <span>Тегов пока нет</span>}
            </div>
            {client.notes.length ? (
              client.notes.map((note) => (
                <article className="message" key={note.id}>
                  <div>{note.content}</div>
                  <small>{new Date(note.created_at).toLocaleString("ru-RU")}</small>
                </article>
              ))
            ) : (
              <div className="empty-state">Заметки сотрудников появятся после ручной работы в CRM.</div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
