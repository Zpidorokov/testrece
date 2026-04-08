import Link from "next/link";

import { StatusPill } from "@/components/status-pill";
import { getClients } from "@/lib/api";

export default async function ClientsPage() {
  const clients = await getClients();

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Client cards</span>
          <h2>Клиенты</h2>
          <p>Карточки клиентов с быстрым переходом в переписку и историю взаимодействия.</p>
        </div>
      </header>
      <section className="panel">
        <h3>Список клиентов</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Имя</th>
              <th>Username</th>
              <th>Статус</th>
              <th>Телефон</th>
            </tr>
          </thead>
          <tbody>
            {clients.length ? (
              clients.map((client) => (
                <tr key={client.id}>
                  <td className="mono">#{client.id}</td>
                  <td>
                    <Link href={`/clients/${client.id}`}>{client.full_name ?? "Без имени"}</Link>
                  </td>
                  <td>{client.username ? `@${client.username}` : "—"}</td>
                  <td>
                    <StatusPill label={client.status} />
                  </td>
                  <td>{client.phone ?? "—"}</td>
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

