"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

const EXAMPLES = [
  "Need to ship 2 x 40HC containers of ceramic tiles from Foshan to Jebel Ali. Cargo ready 20 October. Please quote door-to-door including customs.",
  "Please quote 3 pallets of automotive parts from Shanghai to Dubai, ready around 15 October, including pickup, customs clearance and delivery.",
  "Looking to move 1 x 40HC of stainless steel kitchen sinks from Shanghai to Jebel Ali, ready early November, port to port, FOB.",
];

export default function NewQuotePage() {
  const router = useRouter();
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerId, setCustomerId] = useState<string>("");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listCustomers().then(setCustomers).catch(() => {});
  }, []);

  async function submit() {
    if (!text.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const quote = await api.createQuote({
        raw_text: text,
        customer_id: customerId ? Number(customerId) : null,
      });
      router.push(`/quotes/${quote.id}`);
    } catch (e: any) {
      setError(e.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">New enquiry</h1>
        <p className="mt-1 text-sm text-slate-500">
          Paste the customer's request as received — email, WhatsApp, portal form. The AI Gateway
          extracts a structured shipment requirement, classifies the commodity, and prices it.
        </p>
      </div>

      <Card className="space-y-4">
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Customer (optional)</label>
          <select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Unassigned / new customer</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Enquiry text</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            placeholder="Paste the customer's enquiry here…"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setText(ex)}
                className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 hover:border-slate-400 hover:text-slate-700"
              >
                Example {i + 1}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={submit}
          disabled={submitting || !text.trim()}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-40"
        >
          {submitting ? "Extracting shipment details…" : "Run AI extraction & quote"}
        </button>
      </Card>
    </div>
  );
}
