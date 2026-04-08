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
        <h3>Активные диалоги</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Клиент</th>
              <th>Статус</th>
              <th>Режим</th>
              <th>Последнее сообщение</th>
            </tr>
          </thead>
          <tbody>
            {dialogs.length ? (
              dialogs.slice(0, 8).map((dialog) => (
                <tr key={dialog.id}>
                  <td className="mono" data-label="ID">
                    #{dialog.id}
                  </td>
                  <td data-label="Клиент">
                    <Link href={`/clients/${dialog.client_id}`}>{dialog.client_name ?? `Клиент #${dialog.client_id}`}</Link>
                  </td>
                  <td data-label="Статус">
                    <StatusPill
                      label={formatDialogStatus(dialog.status)}
                      tone={dialog.status === "manual" || dialog.status === "escalated" ? "warning" : "neutral"}
                    />
                  </td>
                  <td data-label="Режим">{formatDialogMode(dialog.mode)}</td>
                  <td data-label="Последнее">{dialog.last_message ?? "Пока без сообщений"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">Пока нет данных. Как только начнут приходить диалоги, таблица заполнится автоматически.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
