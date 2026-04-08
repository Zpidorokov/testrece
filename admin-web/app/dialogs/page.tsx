import Link from "next/link";

import { DialogActions } from "@/components/dialog-actions";
import { StatusPill } from "@/components/status-pill";
import { getDialog, getDialogs } from "@/lib/api";
import { formatDialogMode, formatDialogStatus, formatSenderType } from "@/lib/ui";

type Props = {
  searchParams?: Promise<{ dialog?: string }>;
};

function messageTone(senderType: string) {
  if (senderType === "client") {
    return "message-client";
  }
  if (senderType === "staff") {
    return "message-staff";
  }
  return "message-ai";
}

export default async function DialogsPage({ searchParams }: Props) {
  const dialogs = await getDialogs();
  const params = searchParams ? await searchParams : {};
  const selectedId = Number(params.dialog);
  const selectedDialogId = dialogs.some((dialog) => dialog.id === selectedId) ? selectedId : dialogs[0]?.id;
  const selected = selectedDialogId ? await getDialog(String(selectedDialogId)) : null;

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Операционный чат</span>
          <h2>Диалоги</h2>
          <p>Список обращений, текущая лента и быстрый ручной перехват без лишних экранов.</p>
        </div>
      </header>

      <section className="split-layout">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h3>Очередь диалогов</h3>
              <p className="panel-subtitle">Выберите обращение, чтобы увидеть всю историю и текущий AI-статус.</p>
            </div>
          </div>

          {dialogs.length ? (
            <div className="record-list">
              {dialogs.map((dialog) => {
                const active = dialog.id === selectedDialogId;
                return (
                  <Link
                    className={`record-card record-card-link${active ? " record-card-active" : ""}`}
                    href={`/dialogs?dialog=${dialog.id}`}
                    key={dialog.id}
                  >
                    <div className="record-card-head">
                      <div>
                        <div className="record-card-title">{dialog.client_name ?? `Клиент #${dialog.client_id}`}</div>
                        <div className="record-inline mono">#{dialog.id}</div>
                      </div>
                      <StatusPill
                        label={formatDialogStatus(dialog.status)}
                        tone={dialog.status === "escalated" ? "danger" : dialog.mode === "manual" ? "warning" : "neutral"}
                      />
                    </div>
                    <div className="record-card-meta">
                      <span>{formatDialogMode(dialog.mode)}</span>
                      <span>{dialog.last_message_at ? new Date(dialog.last_message_at).toLocaleString("ru-RU") : "Без ответа"}</span>
                    </div>
                    <p className="record-card-copy">{dialog.last_message ?? "Пока без ответа"}</p>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">Диалоги появятся после первого входящего сообщения в Telegram.</div>
          )}
        </article>

        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <div>
                <h3>Лента переписки</h3>
                <p className="panel-subtitle">Здесь видно, что написал клиент, как ответил ассистент и на каком шаге бронь.</p>
              </div>
              {selected ? (
                <div className="record-inline">
                  <StatusPill label={formatDialogMode(selected.mode)} tone={selected.mode === "manual" ? "warning" : "neutral"} />
                </div>
              ) : null}
            </div>

            {selected ? (
              <div className="messages">
                {selected.messages.map((message) => (
                  <article className={`message ${messageTone(message.sender_type)}`} key={message.id}>
                    <div className="message-role">{formatSenderType(message.sender_type)}</div>
                    <div>{message.text_content ?? "Медиа"}</div>
                    <div className="message-meta">{new Date(message.created_at).toLocaleString("ru-RU")}</div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">Выберите диалог или дождитесь первого обращения.</div>
            )}
          </section>

          {selected ? (
            <>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h3>Авто-сценарий</h3>
                    <p className="panel-subtitle">Внутреннее состояние, чтобы быстро понять, почему AI ждёт ответ или запись.</p>
                  </div>
                </div>
                <div className="status-grid">
                  <div className="status-box">
                    <span>Текущий шаг</span>
                    <strong>{String(selected.ai_flags.last_ai_action ?? "—")}</strong>
                  </div>
                  <div className="status-box">
                    <span>Автоответ</span>
                    <strong>{selected.ai_flags.can_auto_reply ? "Включен" : "Выключен"}</strong>
                  </div>
                  <div className="status-box">
                    <span>Предложено окон</span>
                    <strong>{Array.isArray(selected.ai_flags.offered_slots) ? selected.ai_flags.offered_slots.length : 0}</strong>
                  </div>
                </div>
              </section>

              <section className="panel">
                <h3>Ручные действия</h3>
                <p className="panel-subtitle">Забрать диалог себе, вернуть AI или быстро ответить вручную.</p>
                <DialogActions dialogId={selected.id} mode={selected.mode} />
              </section>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
