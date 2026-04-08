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
          <p className="panel-subtitle">Если нужно помочь вручную: выберите клиента, услугу и точное время.</p>
          <CreateBookingForm services={services} staff={staff} branches={branches} />
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h3>Ближайшие записи</h3>
              <p className="panel-subtitle">Все брони, которые уже дошли до внутреннего booking engine.</p>
            </div>
          </div>
          {bookings.length ? (
            <div className="record-list">
              {bookings.map((booking) => (
                <article className="record-card" key={booking.id}>
                  <div className="record-card-head">
                    <div>
                      <div className="record-card-title">{serviceMap.get(booking.service_id) ?? `Услуга #${booking.service_id}`}</div>
                      <div className="record-inline mono">Бронь #{booking.id}</div>
                    </div>
                    <StatusPill
                      label={formatBookingStatus(booking.status)}
                      tone={booking.status.includes("cancel") ? "danger" : booking.status === "confirmed" ? "success" : "neutral"}
                    />
                  </div>
                  <div className="record-card-meta">
                    <span>Клиент #{booking.client_id}</span>
                    <span>{new Date(booking.start_at).toLocaleString("ru-RU")}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">Записи появятся после создания из Telegram или вручную из панели.</div>
          )}
        </article>
      </section>
    </div>
  );
}
