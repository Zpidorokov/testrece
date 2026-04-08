import { proxyMutation } from "@/lib/mutations";

export async function POST(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyMutation(`/api/dialogs/${id}/return-to-auto`, {
    method: "POST",
  });
}

