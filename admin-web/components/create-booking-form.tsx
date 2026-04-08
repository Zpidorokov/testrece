"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import type { BranchItem, ServiceItem, StaffItem } from "@/lib/types";

export function CreateBookingForm({
  services,
  staff,
  branches,
}: {
  services: ServiceItem[];
  staff: StaffItem[];
  branches: BranchItem[];
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    client_id: "",
    service_id: services[0]?.id?.toString() ?? "",
    staff_id: staff[0]?.id?.toString() ?? "",
    branch_id: branches[0]?.id?.toString() ?? "",
    start_at: "",
    comment: "",
  });

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: Number(form.client_id),
          service_id: Number(form.service_id),
          staff_id: form.staff_id ? Number(form.staff_id) : null,
          branch_id: form.branch_id ? Number(form.branch_id) : null,
          start_at: new Date(form.start_at).toISOString(),
          comment: form.comment || null,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Не удалось создать запись");
      }
      startTransition(() => router.refresh());
      setForm((current) => ({ ...current, client_id: "", start_at: "", comment: "" }));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-grid">
      <input
        className="input"
        placeholder="ID клиента"
        value={form.client_id}
        onChange={(event) => setForm((current) => ({ ...current, client_id: event.target.value }))}
      />
      <select className="input" value={form.service_id} onChange={(event) => setForm((current) => ({ ...current, service_id: event.target.value }))}>
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.name}
          </option>
        ))}
      </select>
      <select className="input" value={form.staff_id} onChange={(event) => setForm((current) => ({ ...current, staff_id: event.target.value }))}>
        {staff.map((item) => (
          <option key={item.id} value={item.id}>
            {item.full_name}
          </option>
        ))}
      </select>
      <select className="input" value={form.branch_id} onChange={(event) => setForm((current) => ({ ...current, branch_id: event.target.value }))}>
        {branches.map((branch) => (
          <option key={branch.id} value={branch.id}>
            {branch.name}
          </option>
        ))}
      </select>
      <input
        className="input"
        type="datetime-local"
        value={form.start_at}
        onChange={(event) => setForm((current) => ({ ...current, start_at: event.target.value }))}
      />
      <textarea
        className="textarea"
        placeholder="Комментарий"
        value={form.comment}
        onChange={(event) => setForm((current) => ({ ...current, comment: event.target.value }))}
      />
      <button className="button" disabled={busy || !form.client_id || !form.start_at} onClick={() => void submit()}>
        Создать запись
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}
