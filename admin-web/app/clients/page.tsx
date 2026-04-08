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
        <div className="panel-head">
          <div>
            <h3>Список клиентов</h3>
            <p className="panel-subtitle">Карточки собираются автоматически после первого обращения в Telegram.</p>
          </div>
        </div>
        {clients.length ? (
          <div className="record-list">
            {clients.map((client) => (
              <Link className="record-card record-card-link" href={`/clients/${client.id}`} key={client.id}>
                <div className="record-card-head">
                  <div>
                    <div className="record-card-title">{client.full_name ?? "Без имени"}</div>
                    <div className="record-inline mono">#{client.id}</div>
                  </div>
                  <StatusPill label={formatClientStatus(client.status)} />
                </div>
                <div className="record-card-meta">
                  <span>{client.username ? `@${client.username}` : "Без username"}</span>
                  <span>{client.phone ?? "Телефон не указан"}</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">Клиенты создаются автоматически при первом сообщении в Telegram Business.</div>
        )}
      </section>
    </div>
  );
}
