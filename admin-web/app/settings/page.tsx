import { getAuditLogs, getBranches, getServices, getStaff } from "@/lib/api";

export default async function SettingsPage() {
  const [services, staff, branches, logs] = await Promise.all([getServices(), getStaff(), getBranches(), getAuditLogs()]);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">System view</span>
          <h2>Настройки</h2>
          <p>Срез по каталогам и последним аудит-событиям, чтобы быстро проверять конфигурацию и поведение системы.</p>
        </div>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Каталоги</h3>
          <div className="stack">
            <div>
              <strong>Services</strong>
              <p className="panel-subtitle">{services.length} элементов</p>
            </div>
            <div>
              <strong>Staff</strong>
              <p className="panel-subtitle">{staff.length} сотрудников</p>
            </div>
            <div>
              <strong>Branches</strong>
              <p className="panel-subtitle">{branches.length} филиалов</p>
            </div>
          </div>
        </article>
        <article className="panel">
          <h3>Последние audit logs</h3>
          <div className="stack">
            {logs.length ? (
              logs.slice(0, 10).map((log) => (
                <article className="message" key={log.id}>
                  <strong>{log.action}</strong>
                  <div>
                    {log.entity_type} #{log.entity_id}
                  </div>
                  <small>{new Date(log.created_at).toLocaleString("ru-RU")}</small>
                </article>
              ))
            ) : (
              <div className="empty-state">Как только backend начнёт обрабатывать события, здесь появится аудит.</div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

