import { CreateBookingForm } from "@/components/create-booking-form";
import { StatusPill } from "@/components/status-pill";
import { getBookings, getBranches, getServices, getStaff } from "@/lib/api";
import { formatBookingStatus } from "@/lib/ui";

export default async function BookingsPage() {
  const [bookings, services, staff, branches] = await Promise.all([getBookings(), getServices(), getStaff(), getBranches()]);
  const serviceMap = new Map(services.map((service) => [service.id, service.name]));

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Календарь</span>
          <h2>Записи</h2>
          <p>Свободные слоты и ручное создание записи.</p>
        </div>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Создать запись</h3>
          <p className="panel-subtitle">Клиент, услуга, мастер и время.</p>
          <CreateBookingForm services={services} staff={staff} branches={branches} />
        </article>

        <article className="panel">
          <h3>Ближайшие записи</h3>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Клиент</th>
                <th>Услуга</th>
                <th>Старт</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {bookings.length ? (
                bookings.map((booking) => (
                  <tr key={booking.id}>
                    <td className="mono" data-label="ID">
                      #{booking.id}
                    </td>
                    <td data-label="Клиент">#{booking.client_id}</td>
                    <td data-label="Услуга">{serviceMap.get(booking.service_id) ?? `#${booking.service_id}`}</td>
                    <td data-label="Старт">{new Date(booking.start_at).toLocaleString("ru-RU")}</td>
                    <td data-label="Статус">
                      <StatusPill
                        label={formatBookingStatus(booking.status)}
                        tone={booking.status.includes("cancel") ? "danger" : booking.status === "confirmed" ? "success" : "neutral"}
                      />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-state">Записи появятся после создания из Telegram или вручную из панели.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </article>
      </section>
    </div>
  );
}
