import React from "react";
import type { RetailerUrlWithLatest } from "@/types/api";
import { formatPrice, deltaIcon, formatShortDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

function DealBadge({ url }: { url: RetailerUrlWithLatest }) {
  // Suppress entirely when 90-day average unavailable or < 3 data points (per D-03, D-05)
  if (url.avg_90d_cents == null || url.avg_90d_count == null || url.avg_90d_count < 3) {
    return null;
  }

  const currentPrice = url.latest_result?.price_cents;
  if (currentPrice == null) return null;

  const isGoodDeal = currentPrice < url.avg_90d_cents;

  return isGoodDeal ? (
    <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
      Good deal
    </Badge>
  ) : (
    <Badge className="bg-red-500/15 text-red-400 border-red-500/30">
      Above avg
    </Badge>
  );
}

function WaybackStats({ url }: { url: RetailerUrlWithLatest }) {
  if (!url.latest_result) return null;

  const segments: React.ReactNode[] = [];

  if (url.price_30d_cents != null && url.date_30d) {
    segments.push(
      <span key="30d">30d: {formatPrice(url.price_30d_cents)} ({formatShortDate(url.date_30d)})</span>
    );
  }
  if (url.price_90d_cents != null && url.date_90d) {
    segments.push(
      <span key="90d">90d: {formatPrice(url.price_90d_cents)} ({formatShortDate(url.date_90d)})</span>
    );
  }
  // Show 90d average only when count >= 3 (per D-05)
  if (url.avg_90d_cents != null && url.avg_90d_count != null && url.avg_90d_count >= 3) {
    segments.push(
      <span key="avg">avg {formatPrice(url.avg_90d_cents)} ({url.avg_90d_count} pts)</span>
    );
  }

  const hasExtremes = url.all_time_low_cents != null || url.all_time_high_cents != null;

  if (segments.length === 0 && !hasExtremes) return null;

  return (
    <>
      {segments.length > 0 && (
        <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
          {segments.map((seg, i) => (
            <span key={i} className="flex items-center">
              {i > 0 && <span className="mr-2">&middot;</span>}
              {seg}
            </span>
          ))}
          <DealBadge url={url} />
        </div>
      )}
      {hasExtremes && (
        <div className="mt-1 flex items-center gap-x-2 text-xs text-muted-foreground">
          {url.all_time_low_cents != null && (
            <span>Low: {formatPrice(url.all_time_low_cents)}</span>
          )}
          {url.all_time_low_cents != null && url.all_time_high_cents != null && (
            <span>&middot;</span>
          )}
          {url.all_time_high_cents != null && (
            <span>High: {formatPrice(url.all_time_high_cents)}</span>
          )}
        </div>
      )}
    </>
  );
}

interface ListingRowProps {
  url: RetailerUrlWithLatest;
  isLowest: boolean;
  thresholdCents: number;
  onViewHistory?: (retailerUrlId: number) => void;
}

export function ListingRow({ url, isLowest, onViewHistory }: ListingRowProps) {
  const result = url.latest_result;

  if (!result) {
    return (
      <div className="flex items-center justify-between py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-muted-foreground">{url.url}</p>
          <p className="text-xs text-muted-foreground">No scrape data yet</p>
        </div>
        <span
          className="ml-4 text-sm text-muted-foreground/50 cursor-not-allowed"
          title="Available in next update"
        >
          View history
        </span>
      </div>
    );
  }

  const deltaColor =
    result.direction === "lower"
      ? "text-emerald-400"
      : result.direction === "higher"
        ? "text-red-400"
        : "text-zinc-400";

  const pctDisplay =
    result.direction === "lower"
      ? `-${Math.abs(result.pct_change).toFixed(1)}%`
      : result.direction === "higher"
        ? `+${Math.abs(result.pct_change).toFixed(1)}%`
        : `${result.pct_change.toFixed(1)}%`;

  return (
    <div className="flex items-center justify-between py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-sm">{result.product_name}</p>
        <div className="mt-1 flex items-center gap-2">
          <span className="font-heading text-lg font-bold">
            {formatPrice(result.price_cents)}
          </span>
          <span className={`text-sm ${deltaColor}`}>
            {deltaIcon(result.direction)} {pctDisplay}
          </span>
          {isLowest && (
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
              Lowest
            </Badge>
          )}
        </div>
        <WaybackStats url={url} />
      </div>
      <button
        onClick={() => onViewHistory?.(url.id)}
        className="ml-4 text-sm text-primary hover:underline cursor-pointer"
      >
        View history
      </button>
    </div>
  );
}
