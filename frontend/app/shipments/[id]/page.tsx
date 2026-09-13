"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, Badge, Field, EmptyState } from "@/components/ui";
import { ErrorPanel } from "@/app/page";
import { AIDecisionLog } from "@/app/quotes/[id]/page";

export default function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [shipment, setShipment] = useState<any>(null);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [selectedEvent, setSelectedEvent] = useState("");
  const [notes, setNotes] = useState("");
  const [location, setLocation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.getShipment(id).then(setShipment).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    api.listEventTypes().then(setEventTypes).catch(() => {});
  }, [id]);

  async function addEvent() {
    if (!selectedEvent) return;
    setSubmitting(true);
    try {
      await api.addShipmentEvent(id, { event_type: selectedEvent, notes: notes || undefined, location: location || undefined });
      setSelectedEvent("");
      setNotes("");
      setLocation("");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <ErrorPanel error={error} />;
  if (!shipment) return <div className="text-sm text-slate-500">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-900">{shipment.code}</h1>
        <Badge text={shipment.stage} />
        <Badge text={shipment.risk_level} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Shipment</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Customer">{shipment.customer?.name}</Field>
            <Field label="Carrier">{shipment.carrier?.name}</Field>
            <Field label="Origin">{shipment.origin?.name}</Field>
            <Field label="Destination">{shipment.destination?.name}</Field>
            <Field label="Mode">{shipment.mode}</Field>
            <Field label="Equipment">{shipment.equipment}</Field>
            <Field label="Order">{shipment.order_code}</Field>
            <Field label="From quote">{shipment.quote_code}</Field>
            <Field label="Vessel/flight">{shipment.vessel_or_flight}</Field>
            <Field label="Cutoff">{shipment.cutoff_date}</Field>
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Document checklist</h2>
          <div className="mt-3 space-y-2">
            {shipment.documents.map((d: any) => (
              <div key={d.id} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2 text-xs">
                <div>
                  <p className="font-medium text-slate-800">{d.document_type.replace(/_/g, " ")}</p>
                  {d.validation_notes && <p className="text-slate-500">{d.validation_notes}</p>}
                </div>
                <div className="flex items-center gap-1.5">
                  <Badge text={d.requirement_level} />
                  <Badge text={d.status} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Add event</h2>
          <div className="mt-3 space-y-2">
            <select
              value={selectedEvent}
              onChange={(e) => setSelectedEvent(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select event…</option>
              {eventTypes.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Location (optional)"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (optional)"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              onClick={addEvent}
              disabled={!selectedEvent || submitting}
              className="w-full rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
            >
              {submitting ? "Recording…" : "Record event"}
            </button>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Timeline</h2>
          <ol className="mt-3 space-y-3 border-l border-slate-200 pl-4">
            {shipment.events.map((e: any) => (
              <li key={e.id} className="relative">
                <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-slate-900" />
                <p className="text-sm font-medium text-slate-800">{e.event_type.replace(/_/g, " ")}</p>
                <p className="text-xs text-slate-400">
                  {new Date(e.event_datetime).toLocaleString()} {e.location ? `· ${e.location}` : ""}
                </p>
                {e.notes && <p className="text-xs text-slate-500">{e.notes}</p>}
              </li>
            ))}
          </ol>
        </Card>

        <div className="space-y-6">
          <Card>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Exceptions</h2>
            <div className="mt-3 space-y-2">
              {shipment.exceptions.length === 0 ? (
                <EmptyState text="No open exceptions." />
              ) : (
                shipment.exceptions.map((e: any) => (
                  <div key={e.id} className="rounded-md border border-slate-100 p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800">{e.exception_type.replace(/_/g, " ")}</span>
                      <Badge text={e.severity} />
                    </div>
                    <p className="mt-1 text-slate-500">{e.reason}</p>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Communications</h2>
            <div className="mt-3 space-y-2">
              {shipment.communications.length === 0 ? (
                <EmptyState text="No communications yet." />
              ) : (
                shipment.communications.map((c: any) => (
                  <div key={c.id} className="rounded-md border border-slate-100 p-3 text-xs">
                    <p className="font-semibold text-slate-800">{c.subject}</p>
                    <p className="mt-1 text-slate-500">{c.body}</p>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Tasks</h2>
            <div className="mt-3 space-y-2">
              {(shipment.tasks || []).length === 0 ? (
                <EmptyState text="No open tasks." />
              ) : (
                shipment.tasks.map((t: any) => (
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
      </div>

      <AIDecisionLog decisions={shipment.ai_decisions} />
    </div>
  );
}
