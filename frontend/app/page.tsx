"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, StatTile, Badge, EmptyState } from "@/components/ui";

export default function ControlTowerPage() {
  const [summary, setSummary] = useState<any>(null);
  const [shipments, setShipments] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.dashboardSummary(), api.listShipments()])
      .then(([s, sh]) => {
        setSummary(s);
        setShipments(sh);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorPanel error={error} />;
  if (!summary) return <div className="text-sm text-slate-500">Loading control tower…</div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Shipment Control Tower</h1>
        <p className="mt-1 text-sm text-slate-500">
          Enquiry → quote → order → booking → delivery, in one shipment intelligence layer.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Quotes total" value={summary.quotes.total} />
        <StatTile label="Awaiting info" value={summary.quotes.draft_or_missing_info} />
        <StatTile label="Quoted" value={summary.quotes.quoted} />
        <StatTile label="Approved" value={summary.quotes.approved} />
        <StatTile label="Quoted value" value={`$${summary.quotes.quoted_value_usd.toLocaleString()}`} />
        <StatTile
          label="Touchless rate"
          value={summary.shipments.touchless_shipment_rate !== null ? `${Math.round(summary.shipments.touchless_shipment_rate * 100)}%` : "—"}
          sub="Shipments with zero open exceptions"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Shipments</h2>
            <Link href="/shipments" className="text-xs font-medium text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="mt-4">
            {shipments.length === 0 ? (
              <EmptyState text="No shipments yet — approve a quote to create one." />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="pb-2">Shipment</th>
                    <th className="pb-2">Customer</th>
                    <th className="pb-2">Lane</th>
                    <th className="pb-2">Stage</th>
                    <th className="pb-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {shipments.slice(0, 8).map((s) => (
                    <tr key={s.id} className="border-b border-slate-50 last:border-0">
                      <td className="py-2">
                        <Link href={`/shipments/${s.id}`} className="font-medium text-blue-600 hover:underline">
                          {s.code}
                        </Link>
                      </td>
                      <td className="py-2 text-slate-600">{s.customer?.name}</td>
                      <td className="py-2 text-slate-600">
                        {s.origin?.name} → {s.destination?.name}
                      </td>
                      <td className="py-2">
                        <Badge text={s.stage} />
                      </td>
                      <td className="py-2">
                        <Badge text={s.risk_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Open exceptions</h2>
          <div className="mt-4 space-y-3">
            {summary.exceptions.items.length === 0 ? (
              <EmptyState text="No open exceptions." />
            ) : (
              summary.exceptions.items.map((e: any) => (
                <div key={e.id} className="rounded-md border border-slate-100 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800">{e.exception_type.replace(/_/g, " ")}</span>
                    <Badge text={e.severity} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{e.reason}</p>
                  {e.recommended_action && (
                    <p className="mt-1 text-xs font-medium text-slate-700">→ {e.recommended_action}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

export function ErrorPanel({ error }: { error: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <p className="font-medium">Couldn't reach the API.</p>
      <p className="mt-1 text-red-600">{error}</p>
      <p className="mt-2 text-xs text-red-500">Is the backend running at NEXT_PUBLIC_API_URL?</p>
    </div>
  );
}
