import Link from "next/link";

import { DialogActions } from "@/components/dialog-actions";
import { StatusPill } from "@/components/status-pill";
import { getDialog, getDialogs } from "@/lib/api";
import { formatDialogMode, formatDialogStatus } from "@/lib/ui";

export default async function DialogsPage() {
  const dialogs = await getDialogs();
  const selected = dialogs[0] ? await getDialog(String(dialogs[0].id)) : null;

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Операционный чат</span>
          <h2>Диалоги</h2>
          <p>Все обращения, текущая переписка и быстрый ручной перехват.</p>
        </div>
      </header>

      <section className="split-layout">
        <div className="panel">
          <h3>Список диалогов</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Клиент</th>
                <th>Статус</th>
                <th>Режим</th>
                <th>Последнее</th>
              </tr>
            </thead>
            <tbody>
              {dialogs.length ? (
                dialogs.map((dialog) => (
                  <tr key={dialog.id}>
                    <td data-label="Клиент">
                      <Link href={`/clients/${dialog.client_id}`}>{dialog.client_name ?? `Клиент #${dialog.client_id}`}</Link>
                    </td>
                    <td data-label="Статус">
                      <StatusPill
                        label={formatDialogStatus(dialog.status)}
                        tone={dialog.status === "escalated" ? "danger" : dialog.mode === "manual" ? "warning" : "neutral"}
                      />
                    </td>
                    <td data-label="Режим">{formatDialogMode(dialog.mode)}</td>
                    <td data-label="Последнее">{dialog.last_message ?? "Пока без ответа"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4}>
                    <div className="empty-state">Диалоги появятся после первого входящего сообщения в Telegram.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="stack">
          <section className="panel">
            <h3>Лента сообщений</h3>
            {selected ? (
              <div className="messages">
                {selected.messages.map((message) => (
                  <article className="message" key={message.id}>
                    <strong>{message.sender_type === "client" ? "Клиент" : message.sender_type === "ai" ? "AI" : "Сотрудник"}</strong>
                    <div>{message.text_content ?? "Медиа"}</div>
                    <small>{new Date(message.created_at).toLocaleString("ru-RU")}</small>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">Выберите диалог или дождитесь первого обращения.</div>
            )}
          </section>

          {selected ? (
            <section className="panel">
              <h3>Ручные действия</h3>
              <p className="panel-subtitle">Перевести в ручной режим, вернуть AI и ответить самому.</p>
              <DialogActions dialogId={selected.id} mode={selected.mode} />
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
