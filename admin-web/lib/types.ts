export type AnalyticsOverview = {
  new_clients: number;
  dialogs_total: number;
  bookings_total: number;
  conversion_to_booking: number;
  avg_first_response_sec: number;
  cancel_rate: number;
  no_show_rate: number;
};

export type DialogSummary = {
  id: number;
  client_id: number;
  client_name?: string | null;
  status: string;
  mode: string;
  assigned_user_id?: number | null;
  risk_flag?: string | null;
  last_message?: string | null;
  last_message_at?: string | null;
};

export type MessageItem = {
  id: number;
  direction: string;
  sender_type: string;
  content_type: string;
  text_content?: string | null;
  created_at: string;
};

export type DialogDetail = {
  id: number;
  client_id: number;
  mode: string;
  status: string;
  assigned_user_id?: number | null;
  forum_thread_id?: number | null;
  messages: MessageItem[];
  ai_flags: Record<string, unknown>;
};

export type ClientCard = {
  id: number;
  name?: string | null;
  telegram_user_id: number;
  username?: string | null;
  phone?: string | null;
  status: string;
  preferred_staff?: number | null;
  preferred_branch?: number | null;
  tags: string[];
  notes: Array<{ id: number; content: string; created_at: string }>;
  last_dialog_at?: string | null;
};

export type ClientSummary = {
  id: number;
  telegram_user_id: number;
  username?: string | null;
  full_name?: string | null;
  phone?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Booking = {
  id: number;
  client_id: number;
  service_id: number;
  staff_id?: number | null;
  branch_id?: number | null;
  start_at: string;
  end_at: string;
  status: string;
  comment?: string | null;
};

export type ServiceItem = {
  id: number;
  name: string;
  duration_min: number;
  price_from?: number | null;
  price_to?: number | null;
};

export type StaffItem = {
  id: number;
  full_name: string;
  specialization?: string | null;
  branch_id?: number | null;
};

export type BranchItem = {
  id: number;
  name: string;
  address?: string | null;
  timezone: string;
};

export type KnowledgeItem = {
  id: number;
  kind: string;
  title: string;
  content: string;
  metadata_json: Record<string, unknown>;
  is_active: boolean;
};

export type AuditLog = {
  id: number;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
};

