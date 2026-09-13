"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Badge, EmptyState } from "@/components/ui";
import { ErrorPanel } from "@/app/page";

export default function ShipmentsListPage() {
  const [shipments, setShipments] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listShipments().then(setShipments).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorPanel error={error} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Shipments</h1>
        <p className="mt-1 text-sm text-slate-500">Every order created from an approved quote, tracked to delivery.</p>
      </div>

      <Card>
        {!shipments ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : shipments.length === 0 ? (
          <EmptyState text="No shipments yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-2">Shipment</th>
                <th className="pb-2">Customer</th>
                <th className="pb-2">Carrier</th>
                <th className="pb-2">Lane</th>
                <th className="pb-2">Stage</th>
                <th className="pb-2">Risk</th>
              </tr>
            </thead>
            <tbody>
              {shipments.map((s) => (
                <tr key={s.id} className="border-b border-slate-50 last:border-0">
                  <td className="py-2">
                    <Link href={`/shipments/${s.id}`} className="font-medium text-blue-600 hover:underline">
                      {s.code}
                    </Link>
                  </td>
                  <td className="py-2 text-slate-600">{s.customer?.name}</td>
                  <td className="py-2 text-slate-600">{s.carrier?.name ?? "—"}</td>
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
      </Card>
    </div>
  );
}
