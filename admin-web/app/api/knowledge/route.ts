import { proxyMutation } from "@/lib/mutations";

export async function POST(request: Request) {
  const payload = await request.text();
  return proxyMutation("/api/knowledge", {
    method: "POST",
    body: payload,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
