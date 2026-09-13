const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  listCustomers: () => request("/customers"),
  listCarriers: () => request("/carriers"),
  listLocations: () => request("/locations"),
  listEventTypes: () => request("/event-types"),

  listQuotes: () => request("/quotes"),
  getQuote: (id: number | string) => request(`/quotes/${id}`),
  createQuote: (payload: { raw_text: string; customer_id?: number | null; source?: string }) =>
    request("/quotes", { method: "POST", body: JSON.stringify(payload) }),
  approveQuote: (id: number | string, optionId: number) =>
    request(`/quotes/${id}/approve`, { method: "POST", body: JSON.stringify({ option_id: optionId }) }),

  listShipments: () => request("/shipments"),
  getShipment: (id: number | string) => request(`/shipments/${id}`),
  addShipmentEvent: (id: number | string, payload: { event_type: string; location?: string; notes?: string }) =>
    request(`/shipments/${id}/events`, { method: "POST", body: JSON.stringify(payload) }),

  dashboardSummary: () => request("/dashboard/summary"),
};
