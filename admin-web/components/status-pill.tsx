export function StatusPill({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "success" | "warning" | "danger" }) {
  return <span className={`pill pill-${tone}`}>{label}</span>;
}

