import type {
  WatchQueryResponse,
  WatchQueryDetailResponse,
  WatchQueryCreate,
  WatchQueryUpdate,
  AlertResponse,
  UnreadCountResponse,
  ScrapeJobResponse,
  HistoryRecord,
} from "@/types/api";

const API_BASE = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  watchQueries: {
    list: () => apiFetch<WatchQueryResponse[]>("/watch-queries/"),
    detail: (id: number) =>
      apiFetch<WatchQueryDetailResponse>(`/watch-queries/${id}`),
    create: (data: WatchQueryCreate) =>
      apiFetch<WatchQueryResponse>("/watch-queries/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: WatchQueryUpdate) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      apiFetch<void>(`/watch-queries/${id}`, { method: "DELETE" }),
    pause: (id: number) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: false }),
      }),
    resume: (id: number) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: true }),
      }),
    scrape: (id: number) =>
      apiFetch<ScrapeJobResponse>(`/watch-queries/${id}/scrape`, {
        method: "POST",
      }),
  },
  retailerUrls: {
    history: (id: number) =>
      apiFetch<HistoryRecord[]>(`/retailer-urls/${id}/history`),
  },
  alerts: {
    list: (limit?: number) =>
      apiFetch<AlertResponse[]>(`/alerts/?limit=${limit ?? 50}`),
    unreadCount: () =>
      apiFetch<UnreadCountResponse>("/alerts/unread-count"),
    markRead: (id: number) =>
      apiFetch<AlertResponse>(`/alerts/${id}/read`, { method: "PATCH" }),
    dismissAll: () =>
      apiFetch<{ dismissed_count: number }>("/alerts/dismiss-all", {
        method: "POST",
      }),
  },
};
