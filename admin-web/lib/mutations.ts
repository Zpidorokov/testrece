import { cookies } from "next/headers";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ENV_ADMIN_TOKEN = process.env.BOTRECEPTIONIST_ADMIN_TOKEN ?? "";

export async function proxyMutation(path: string, options: RequestInit): Promise<Response> {
  const cookieStore = await cookies();
  const runtimeToken = cookieStore.get("admin_token")?.value ?? ENV_ADMIN_TOKEN;
  if (!runtimeToken) {
    return Response.json(
      { ok: false, message: "Set BOTRECEPTIONIST_ADMIN_TOKEN for mutating actions." },
      { status: 503 },
    );
  }

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${runtimeToken}`);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json",
    },
  });
}
