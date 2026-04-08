import { CreateBookingForm } from "@/components/create-booking-form";
import { StatusPill } from "@/components/status-pill";
import { getBookings, getBranches, getServices, getStaff } from "@/lib/api";

export default async function BookingsPage() {
  const [bookings, services, staff, branches] = await Promise.all([getBookings(), getServices(), getStaff(), getBranches()]);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">Internal scheduling</span>
          <h2>Записи</h2>
          <p>Внутренний booking engine v1: одна услуга на запись, подбор слотов и ручное создание из CRM.</p>
        </div>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Создать запись</h3>
          <p className="panel-subtitle">Для реального потока staff заполняет клиента, услугу, мастера и время.</p>
          <CreateBookingForm services={services} staff={staff} branches={branches} />
        </article>

        <article className="panel">
          <h3>Ближайшие записи</h3>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Client</th>
                <th>Service</th>
                <th>Start</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {bookings.length ? (
                bookings.map((booking) => (
                  <tr key={booking.id}>
                    <td className="mono">#{booking.id}</td>
                    <td>{booking.client_id}</td>
                    <td>{booking.service_id}</td>
                    <td>{new Date(booking.start_at).toLocaleString("ru-RU")}</td>
                    <td>
                      <StatusPill
                        label={booking.status}
                        tone={booking.status.includes("cancel") ? "danger" : booking.status === "confirmed" ? "success" : "neutral"}
                      />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-state">Записи появятся после создания из Telegram flow или вручную из CRM.</div>
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

