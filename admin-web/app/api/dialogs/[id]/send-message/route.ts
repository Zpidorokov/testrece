import { proxyMutation } from "@/lib/mutations";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const payload = await request.text();
  return proxyMutation(`/api/dialogs/${id}/send-message`, {
    method: "POST",
    body: payload,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

