import type { RetailerUrlWithLatest } from "@/types/api";
import { formatPrice, deltaIcon } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

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
