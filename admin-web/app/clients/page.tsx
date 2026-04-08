import Link from "next/link";

import { StatusPill } from "@/components/status-pill";
import { getClients } from "@/lib/api";
import { formatClientStatus } from "@/lib/ui";

export default async function ClientsPage() {
  const clients = await getClients();

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">CRM</span>
          <h2>Клиенты</h2>
          <p>Карточки клиентов и быстрый переход к переписке.</p>
        </div>
      </header>
      <section className="panel">
        <h3>Список клиентов</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Имя</th>
              <th>Telegram</th>
              <th>Статус</th>
              <th>Телефон</th>
            </tr>
          </thead>
          <tbody>
            {clients.length ? (
              clients.map((client) => (
                <tr key={client.id}>
                  <td className="mono" data-label="ID">
                    #{client.id}
                  </td>
                  <td data-label="Имя">
                    <Link href={`/clients/${client.id}`}>{client.full_name ?? "Без имени"}</Link>
                  </td>
                  <td data-label="Telegram">{client.username ? `@${client.username}` : "—"}</td>
                  <td data-label="Статус">
                    <StatusPill label={formatClientStatus(client.status)} />
                  </td>
                  <td data-label="Телефон">{client.phone ?? "—"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">Клиенты создаются автоматически при первом сообщении в Telegram Business.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
