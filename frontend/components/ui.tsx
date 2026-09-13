export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-200 bg-white p-5 ${className}`}>{children}</div>;
}

export function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </Card>
  );
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  MISSING_INFO: "bg-amber-100 text-amber-800",
  QUOTED: "bg-blue-100 text-blue-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  EXPIRED: "bg-slate-100 text-slate-500",
  REJECTED: "bg-red-100 text-red-700",
  OPEN: "bg-amber-100 text-amber-800",
  RESOLVED: "bg-emerald-100 text-emerald-800",
  LOW: "bg-emerald-100 text-emerald-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
};

export function Badge({ text }: { text: string }) {
  const cls = STATUS_COLORS[text] || "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {text.replace(/_/g, " ")}
    </span>
  );
}

export function ConfidencePill({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return null;
  const pct = Math.round(value * 100);
  const cls = pct >= 85 ? "bg-emerald-100 text-emerald-800" : pct >= 60 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-700";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{pct}% confidence</span>;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 text-sm text-slate-800">{children ?? <span className="text-slate-400">—</span>}</div>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">{text}</div>;
}
