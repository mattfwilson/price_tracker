export interface RetailerUrlResponse {
  id: number;
  url: string;
  created_at: string;
}

export interface LatestScrapeResult {
  product_name: string;
  price_cents: number;
  listing_url: string;
  scraped_at: string;
  direction: "new" | "higher" | "lower" | "unchanged";
  delta_cents: number;
  pct_change: number;
}

export interface RetailerUrlWithLatest {
  id: number;
  url: string;
  created_at: string;
  latest_result: LatestScrapeResult | null;
}

export interface WatchQueryResponse {
  id: number;
  name: string;
  threshold_cents: number;
  is_active: boolean;
  schedule: string;
  retailer_urls: RetailerUrlResponse[];
  created_at: string;
  updated_at: string;
}

export interface WatchQueryDetailResponse {
  id: number;
  name: string;
  threshold_cents: number;
  is_active: boolean;
  schedule: string;
  retailer_urls: RetailerUrlWithLatest[];
  created_at: string;
  updated_at: string;
}

export interface WatchQueryCreate {
  name: string;
  threshold_cents: number;
  urls: string[];
  schedule: string;
}

export interface WatchQueryUpdate {
  name?: string;
  threshold_cents?: number;
  is_active?: boolean;
  schedule?: string;
  urls?: string[];
}

export interface AlertResponse {
  id: number;
  watch_query_id: number;
  watch_query_name: string;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertSSEPayload {
  alert_id: number;
  watch_query_id: number;
  watch_query_name: string;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  created_at: string;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface ScrapeJobResponse {
  job_id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  results: ScrapeResultResponse[];
}

export interface ScrapeResultResponse {
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  scraped_at: string;
  direction: string;
  delta_cents: number;
  pct_change: number;
}

export interface HistoryRecord {
  id: number;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  scraped_at: string;
  direction: "new" | "higher" | "lower" | "unchanged";
  delta_cents: number;
  pct_change: number;
}
