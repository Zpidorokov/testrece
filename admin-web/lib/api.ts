import "server-only";

import { cookies } from "next/headers";

import type {
  AnalyticsOverview,
  AuditLog,
  Booking,
  BranchItem,
  ClientCard,
  ClientSummary,
  DialogDetail,
  DialogSummary,
  KnowledgeItem,
  ServiceItem,
  StaffItem,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ENV_ADMIN_TOKEN = process.env.BOTRECEPTIONIST_ADMIN_TOKEN ?? "";

const fallbackOverview: AnalyticsOverview = {
  new_clients: 0,
  dialogs_total: 0,
  bookings_total: 0,
  conversion_to_booking: 0,
  avg_first_response_sec: 0,
  cancel_rate: 0,
  no_show_rate: 0,
};

const fallbackDialogs: DialogSummary[] = [];
const fallbackClients: ClientSummary[] = [];
const fallbackBookings: Booking[] = [];
const fallbackKnowledge: KnowledgeItem[] = [];
const fallbackServices: ServiceItem[] = [];
const fallbackStaff: StaffItem[] = [];
const fallbackBranches: BranchItem[] = [];
const fallbackLogs: AuditLog[] = [];

async function request<T>(path: string, fallback: T): Promise<T> {
  const cookieStore = await cookies();
  const runtimeToken = cookieStore.get("admin_token")?.value ?? ENV_ADMIN_TOKEN;
  if (!runtimeToken) {
    return fallback;
  }
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: runtimeToken
        ? {
            Authorization: `Bearer ${runtimeToken}`,
          }
        : undefined,
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function getOverview(): Promise<AnalyticsOverview> {
  return request("/api/analytics/overview", fallbackOverview);
}

export async function getDialogs(): Promise<DialogSummary[]> {
  return request("/api/dialogs", fallbackDialogs);
}

export async function getDialog(id: string): Promise<DialogDetail | null> {
  return request<DialogDetail | null>(`/api/dialogs/${id}`, null);
}

export async function getClients(): Promise<ClientSummary[]> {
  return request("/api/clients", fallbackClients);
}

export async function getClient(id: string): Promise<ClientCard | null> {
  return request<ClientCard | null>(`/api/clients/${id}`, null);
}

export async function getBookings(): Promise<Booking[]> {
  return request("/api/bookings", fallbackBookings);
}

export async function getKnowledge(): Promise<KnowledgeItem[]> {
  return request("/api/knowledge", fallbackKnowledge);
}

export async function getServices(): Promise<ServiceItem[]> {
  return request("/api/services", fallbackServices);
}

export async function getStaff(): Promise<StaffItem[]> {
  return request("/api/staff", fallbackStaff);
}

export async function getBranches(): Promise<BranchItem[]> {
  return request("/api/branches", fallbackBranches);
}

export async function getAuditLogs(): Promise<AuditLog[]> {
  return request("/api/system/audit-logs", fallbackLogs);
}
