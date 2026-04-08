import Link from "next/link";

import { DialogActions } from "@/components/dialog-actions";
import { StatusPill } from "@/components/status-pill";
import { getDialog, getDialogs } from "@/lib/api";

export default async function DialogsPage() {
  const dialogs = await getDialogs();
  const selected = dialogs[0] ? await getDialog(String(dialogs[0].id)) : null;

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Операционный чат</span>
          <h2>Диалоги</h2>
          <p>Список обращений, текущая переписка и takeover.</p>
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
                    <td>
                      <Link href={`/clients/${dialog.client_id}`}>{dialog.client_name ?? `Client ${dialog.client_id}`}</Link>
                    </td>
                    <td>
                      <StatusPill
                        label={dialog.status}
                        tone={dialog.status === "escalated" ? "danger" : dialog.mode === "manual" ? "warning" : "neutral"}
                      />
                    </td>
                    <td>{dialog.mode}</td>
                    <td>{dialog.last_message ?? "..."}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4}>
                    <div className="empty-state">Диалоги появятся после первого Telegram update.</div>
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
                    <strong>{message.sender_type}</strong>
                    <div>{message.text_content ?? "media"}</div>
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
              <p className="panel-subtitle">Перевод в manual, возврат в auto и ручная отправка.</p>
              <DialogActions dialogId={selected.id} mode={selected.mode} />
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
