import Link from "next/link";

import { MetricCard } from "@/components/metric-card";
import { StatusPill } from "@/components/status-pill";
import { getDialogs, getOverview } from "@/lib/api";

export default async function DashboardPage() {
  const [overview, dialogs] = await Promise.all([getOverview(), getDialogs()]);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Core CRM v1</span>
          <h2>Dashboard</h2>
          <p>
            Живой срез по новым обращениям, записи и ручным диалогам. В этой версии Web App заточен
            под быстрый операционный контур салона.
          </p>
        </div>
      </header>

      <section className="grid grid-4">
        <MetricCard label="Новые клиенты" value={overview.new_clients} hint="Воронка начинает считаться с первого Telegram обращения." />
        <MetricCard label="Диалоги" value={overview.dialogs_total} hint="С учётом авто и manual режимов." />
        <MetricCard label="Записи" value={overview.bookings_total} hint="Только внутренний booking engine v1." />
        <MetricCard
          label="Средний первый ответ"
          value={`${overview.avg_first_response_sec.toFixed(0)}s`}
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
                  <td className="mono">#{dialog.id}</td>
                  <td>
                    <Link href={`/clients/${dialog.client_id}`}>{dialog.client_name ?? `Client ${dialog.client_id}`}</Link>
                  </td>
                  <td>
                    <StatusPill
                      label={dialog.status}
                      tone={dialog.status === "manual" || dialog.status === "escalated" ? "warning" : "neutral"}
                    />
                  </td>
                  <td>{dialog.mode}</td>
                  <td>{dialog.last_message ?? "Пока без сообщений"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">Пока нет данных из backend. После запуска API таблица заполнится автоматически.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

