import { cookies } from "next/headers";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const NORMALIZED_API_BASE = API_BASE.replace(/\/admin\/?$/, "").replace(/\/$/, "");

export async function POST(request: Request) {
  const payload = await request.json();
  const response = await fetch(`${NORMALIZED_API_BASE}/api/admin/session/init`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  if (!response.ok) {
    if (response.status === 404) {
      return Response.json({ ok: false, skipped: true });
    }

    let message = "Не удалось открыть рабочую панель.";
    try {
      const parsed = JSON.parse(text) as { detail?: string; message?: string };
      message = parsed.detail ?? parsed.message ?? message;
    } catch {
      if (text.trim()) {
        message = text.trim();
      }
    }

    return Response.json({ ok: false, message }, { status: response.status });
  }

  const parsed = JSON.parse(text) as { token: string };
  const cookieStore = await cookies();
  cookieStore.set("admin_token", parsed.token, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 60 * 60 * 12,
  });

  return Response.json({ ok: true });
}
