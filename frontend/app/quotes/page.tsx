"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Badge, ConfidencePill, EmptyState } from "@/components/ui";
import { ErrorPanel } from "@/app/page";

export default function QuotesListPage() {
  const [quotes, setQuotes] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listQuotes().then(setQuotes).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorPanel error={error} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Quotes</h1>
          <p className="mt-1 text-sm text-slate-500">Every enquiry, its extraction confidence and current status.</p>
        </div>
        <Link href="/quotes/new" className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
          New enquiry
        </Link>
      </div>

      <Card>
        {!quotes ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : quotes.length === 0 ? (
          <EmptyState text="No quotes yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-2">Quote</th>
                <th className="pb-2">Customer</th>
                <th className="pb-2">Lane</th>
                <th className="pb-2">Commodity</th>
                <th className="pb-2">Confidence</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr key={q.id} className="border-b border-slate-50 last:border-0">
                  <td className="py-2">
                    <Link href={`/quotes/${q.id}`} className="font-medium text-blue-600 hover:underline">
                      {q.code}
                    </Link>
                  </td>
                  <td className="py-2 text-slate-600">{q.customer?.name ?? "—"}</td>
                  <td className="py-2 text-slate-600">
                    {q.origin?.name ?? "?"} → {q.destination?.name ?? "?"}
                  </td>
                  <td className="py-2 text-slate-600">{q.cargo_description ?? "—"}</td>
                  <td className="py-2">
                    <ConfidencePill value={q.extraction_confidence} />
                  </td>
                  <td className="py-2">
                    <Badge text={q.status} />
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
