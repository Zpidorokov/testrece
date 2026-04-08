import { proxyMutation } from "@/lib/mutations";

type Props = {
  params: Promise<{ id: string }>;
};

export async function PATCH(request: Request, { params }: Props) {
  const { id } = await params;
  const payload = await request.text();
  return proxyMutation(`/api/knowledge/${id}`, {
    method: "PATCH",
    body: payload,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function DELETE(_: Request, { params }: Props) {
  const { id } = await params;
  return proxyMutation(`/api/knowledge/${id}`, {
    method: "DELETE",
  });
}
