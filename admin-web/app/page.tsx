import Link from "next/link";

import { MetricCard } from "@/components/metric-card";
import { StatusPill } from "@/components/status-pill";
import { getDialogs, getOverview } from "@/lib/api";
import { formatDialogMode, formatDialogStatus } from "@/lib/ui";

export default async function DashboardPage() {
  const [overview, dialogs] = await Promise.all([getOverview(), getDialogs()]);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Сегодня</span>
          <h2>Сводка</h2>
          <p>Новые обращения, диалоги и записи в одном экране.</p>
        </div>
      </header>

      <section className="grid grid-4">
        <MetricCard label="Новые клиенты" value={overview.new_clients} hint="Воронка начинает считаться с первого Telegram обращения." />
        <MetricCard label="Диалоги" value={overview.dialogs_total} hint="С учетом автоответа и ручного режима." />
        <MetricCard label="Записи" value={overview.bookings_total} hint="Считаются только записи из встроенного контура." />
        <MetricCard
          label="Средний первый ответ"
          value={`${overview.avg_first_response_sec.toFixed(0)} c`}
          hint="Считается по первой входящей и первой исходящей реплике."
        />
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h3>Активные диалоги</h3>
            <p className="panel-subtitle">Последние обращения, которые сейчас в работе.</p>
          </div>
          <Link className="button button-ghost" href="/dialogs">
            Все диалоги
          </Link>
        </div>
        {dialogs.length ? (
          <div className="record-list compact-list">
            {dialogs.slice(0, 8).map((dialog) => (
              <Link className="record-card record-card-link" href={`/dialogs?dialog=${dialog.id}`} key={dialog.id}>
                <div className="record-card-head">
                  <div>
                    <div className="record-card-title">{dialog.client_name ?? `Клиент #${dialog.client_id}`}</div>
                    <div className="record-inline mono">#{dialog.id}</div>
                  </div>
                  <StatusPill
                    label={formatDialogStatus(dialog.status)}
                    tone={dialog.status === "manual" || dialog.status === "escalated" ? "warning" : "neutral"}
                  />
                </div>
                <div className="record-card-meta">
                  <span>{formatDialogMode(dialog.mode)}</span>
                  <span>{dialog.last_message_at ? new Date(dialog.last_message_at).toLocaleString("ru-RU") : "Без ответа"}</span>
                </div>
                <p className="record-card-copy">{dialog.last_message ?? "Пока без сообщений"}</p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">Пока нет данных. Как только начнут приходить диалоги, список заполнится автоматически.</div>
        )}
      </section>
    </div>
  );
}
