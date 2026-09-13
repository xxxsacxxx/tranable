"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, Badge, ConfidencePill, Field, EmptyState } from "@/components/ui";
import { ErrorPanel } from "@/app/page";

export default function QuoteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [quote, setQuote] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState<number | null>(null);

  function load() {
    api.getQuote(id).then(setQuote).catch((e) => setError(e.message));
  }

  useEffect(load, [id]);

  async function approve(optionId: number) {
    setApproving(optionId);
    try {
      const shipment = await api.approveQuote(id, optionId);
      router.push(`/shipments/${shipment.id}`);
    } catch (e: any) {
      setError(e.message);
      setApproving(null);
    }
  }

  if (error) return <ErrorPanel error={error} />;
  if (!quote) return <div className="text-sm text-slate-500">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-slate-900">{quote.code}</h1>
            <Badge text={quote.status} />
            <ConfidencePill value={quote.extraction_confidence} />
          </div>
          <p className="mt-1 text-sm text-slate-500">{quote.customer?.name ?? "Unassigned customer"}</p>
        </div>
      </div>

      <Card>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Original request</h2>
        <p className="mt-2 text-sm text-slate-700 whitespace-pre-wrap">{quote.raw_request_text}</p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Shipment requirement</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Origin">{quote.origin?.name}</Field>
            <Field label="Destination">{quote.destination?.name}</Field>
            <Field label="Origin gateway">{quote.origin_port?.name}</Field>
            <Field label="Destination gateway">{quote.destination_port?.name}</Field>
            <Field label="Mode">{quote.mode}</Field>
            <Field label="Equipment">{quote.equipment}</Field>
            <Field label="Quantity">{quote.quantity}</Field>
            <Field label="Service type">{quote.service_type}</Field>
            <Field label="Incoterm">{quote.incoterm}</Field>
            <Field label="Ready date">{quote.ready_date}</Field>
            <Field label="Cargo">{quote.cargo_description}</Field>
            <Field label="Customs clearance">{quote.customs_clearance_required ? "Required" : "—"}</Field>
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Extraction — known / inferred / missing</h2>
          <div className="mt-3 space-y-3">
            <FieldGroup label="Known" items={quote.known_fields} color="emerald" />
            <FieldGroup label="Inferred" items={quote.inferred_fields} color="amber" />
            <FieldGroup label="Missing" items={quote.missing_fields} color="red" />
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">HS classification candidates</h2>
          <div className="mt-3 space-y-2">
            {(quote.hs_candidates || []).length === 0 ? (
              <EmptyState text="No cargo description to classify yet." />
            ) : (
              quote.hs_candidates.map((c: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2 text-sm">
                  <div>
                    <span className="font-mono font-medium text-slate-800">{c.code}</span>
                    <span className="ml-2 text-xs text-slate-500">{c.description}</span>
                  </div>
                  <span className="text-xs font-semibold text-slate-600">{Math.round(c.confidence * 100)}%</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Quote options</h2>
        {quote.options.length === 0 ? (
          <div className="mt-3">
            <EmptyState text="No rate available for this lane/equipment yet — check exceptions or add a rate card." />
          </div>
        ) : (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {quote.options.map((o: any) => (
              <div
                key={o.id}
                className={`rounded-lg border p-4 ${o.is_recommended ? "border-slate-900 ring-1 ring-slate-900" : "border-slate-200"}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-900">{o.label}</span>
                  {o.is_recommended && <Badge text="RECOMMENDED" />}
                </div>
                <p className="mt-1 text-xs text-slate-500">{o.carrier?.name}</p>
                <p className="mt-3 text-2xl font-semibold text-slate-900">
                  {o.currency} {o.customer_price.toLocaleString()}
                </p>
                <p className="text-xs text-slate-500">
                  {o.transit_days} days transit · reliability {Math.round((o.reliability_score || 0) * 100)}%
                </p>
                <div className="mt-3 space-y-1 text-xs text-slate-500">
                  <BreakdownRow label="Base freight" value={o.breakdown.base_freight} />
                  <BreakdownRow label="Origin charges" value={o.breakdown.origin_charges} />
                  <BreakdownRow label="Destination charges" value={o.breakdown.destination_charges} />
                  <BreakdownRow label="Customs" value={o.breakdown.customs_charges} />
                  <BreakdownRow label="Trucking" value={o.breakdown.trucking_charges} />
                  <BreakdownRow label="Documentation" value={o.breakdown.documentation_charges} />
                  <BreakdownRow label="Fuel surcharge" value={o.breakdown.surcharges} />
                  <BreakdownRow label="Risk contingency" value={o.breakdown.risk_contingency} />
                  <BreakdownRow label="Margin" value={o.breakdown.margin} />
                </div>
                <p className="mt-2 text-xs text-slate-400">Win probability ~{Math.round(o.win_probability * 100)}%</p>
                {quote.status === "QUOTED" && (
                  <button
                    onClick={() => approve(o.id)}
                    disabled={approving !== null}
                    className="mt-4 w-full rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
                  >
                    {approving === o.id ? "Converting to order…" : "Approve & convert to order"}
                  </button>
                )}
                {quote.approved_option_id === o.id && (
                  <p className="mt-3 text-center text-xs font-semibold text-emerald-700">✓ Approved</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Communications</h2>
          <div className="mt-3 space-y-3">
            {(quote.communications || []).length === 0 ? (
              <EmptyState text="No communications generated yet." />
            ) : (
              quote.communications.map((c: any) => (
                <div key={c.id} className="rounded-md border border-slate-100 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800">{c.subject}</span>
                    <span className="text-[10px] uppercase text-slate-400">{c.generated_by}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">{c.body}</p>
                </div>
              ))
            )}
          </div>
        </Card>
        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Tasks</h2>
          <div className="mt-3 space-y-2">
            {(quote.tasks || []).length === 0 ? (
              <EmptyState text="No open tasks." />
            ) : (
              quote.tasks.map((t: any) => (
                <div key={t.id} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2 text-xs">
                  <div>
                    <p className="font-medium text-slate-800">{t.title}</p>
                    <p className="text-slate-500">{t.description}</p>
                  </div>
                  <Badge text={t.owner_role} />
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <AIDecisionLog decisions={quote.ai_decisions} />
    </div>
  );
}

export function AIDecisionLog({ decisions }: { decisions: any[] }) {
  return (
    <Card>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        AI decision log <span className="normal-case text-slate-300">— full audit trail, per decision</span>
      </h2>
      <div className="mt-3 space-y-2">
        {(!decisions || decisions.length === 0) ? (
          <EmptyState text="No AI decisions recorded yet." />
        ) : (
          decisions.map((d: any) => (
            <details key={d.id} className="rounded-md border border-slate-100 px-3 py-2 text-xs">
              <summary className="cursor-pointer list-none">
                <span className="inline-flex items-center gap-2">
                  <span className="font-mono font-semibold text-slate-700">{d.task}</span>
                  <span className="text-slate-400">{d.model}</span>
                  {d.confidence !== null && <ConfidencePill value={d.confidence} />}
                </span>
              </summary>
              <div className="mt-2 space-y-1 text-slate-600">
                {d.facts?.length > 0 && (
                  <p>
                    <span className="font-medium text-slate-500">Facts: </span>
                    {d.facts.join("; ")}
                  </p>
                )}
                {d.inferences?.length > 0 && (
                  <p>
                    <span className="font-medium text-slate-500">Inferences: </span>
                    {d.inferences.join("; ")}
                  </p>
                )}
                {d.evidence?.length > 0 && (
                  <p>
                    <span className="font-medium text-slate-500">Evidence: </span>
                    {d.evidence.join("; ")}
                  </p>
                )}
                {d.recommended_action && (
                  <p>
                    <span className="font-medium text-slate-500">Recommended action: </span>
                    {d.recommended_action}
                  </p>
                )}
                <p className="text-slate-400">{new Date(d.timestamp).toLocaleString()}</p>
              </div>
            </details>
          ))
        )}
      </div>
    </Card>
  );
}

function FieldGroup({ label, items, color }: { label: string; items: string[]; color: string }) {
  const dot: Record<string, string> = { emerald: "bg-emerald-500", amber: "bg-amber-500", red: "bg-red-500" };
  return (
    <div>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {(!items || items.length === 0) && <span className="text-xs text-slate-300">none</span>}
        {items?.map((f) => (
          <span key={f} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            <span className={`h-1.5 w-1.5 rounded-full ${dot[color]}`} />
            {f.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    </div>
  );
}

function BreakdownRow({ label, value }: { label: string; value: number }) {
  if (!value) return null;
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span>{value.toLocaleString()}</span>
    </div>
  );
}
