import { useState } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { formatPrice, deltaIcon, formatRelativeTime } from "@/lib/format";
import { useWatchQueryDetail, useScrapeNow } from "@/hooks/use-watch-queries";
import { StatusDot, deriveStatus } from "./StatusDot";
import { CardMenu } from "./CardMenu";
import type { WatchQueryResponse } from "@/types/api";

interface QueryCardProps {
  query: WatchQueryResponse;
  onCardClick: (id: number) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

export function isThresholdBreached(
  prices: (number | null | undefined)[],
  thresholdCents: number
): boolean {
  const validPrices = prices.filter(
    (p): p is number => p != null
  );
  if (validPrices.length === 0) return false;
  return Math.min(...validPrices) <= thresholdCents;
}

export function QueryCard({ query, onCardClick, onEdit, onDelete }: QueryCardProps) {
  const { data: detail, isLoading: detailLoading } = useWatchQueryDetail(query.id);
  const scrapeNowMutation = useScrapeNow();
  const [isScrapingLocal, setIsScrapingLocal] = useState(false);

  const status = deriveStatus(detail, isScrapingLocal);

  // Compute price data from detail
  const prices = detail?.retailer_urls.map((u) => u.latest_result?.price_cents) ?? [];
  const validPrices = prices.filter((p): p is number => p != null);
  const lowestPrice = validPrices.length > 0 ? Math.min(...validPrices) : null;
  const breached = lowestPrice !== null && lowestPrice <= query.threshold_cents;

  // Find the retailer_url with the lowest price for delta info
  const lowestUrl = detail?.retailer_urls.find(
    (u) => u.latest_result?.price_cents === lowestPrice
  );
  const lowestResult = lowestUrl?.latest_result ?? null;

  // Most recent scraped_at across all retailer_urls
  const scrapedAtDates = detail?.retailer_urls
    .map((u) => u.latest_result?.scraped_at)
    .filter((d): d is string => d != null) ?? [];
  const latestScrapedAt =
    scrapedAtDates.length > 0
      ? scrapedAtDates.sort().reverse()[0]
      : null;

  function handleScrapeNow() {
    setIsScrapingLocal(true);
    scrapeNowMutation.mutate(query.id, {
      onSettled: () => {
        setIsScrapingLocal(false);
        toast(`Scrape started for ${query.name}`);
      },
    });
  }

  function deltaColor(direction: string): string {
    switch (direction) {
      case "lower":
        return "text-emerald-600";
      case "higher":
        return "text-red-500";
      default:
        return "text-zinc-400";
    }
  }

  return (
    <Card
      className={cn(
        "cursor-pointer hover:shadow-md transition-shadow duration-150 min-h-[200px]",
        breached && "border-l-[3px] border-l-emerald-500"
      )}
      onClick={() => onCardClick(query.id)}
    >
      {/* Header area */}
      <div className="flex items-start justify-between p-6 pb-0">
        <h3 className="font-heading text-xl font-bold truncate flex-1 mr-2">
          {query.name}
        </h3>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="secondary" className="text-xs">
            {query.retailer_urls.length} url{query.retailer_urls.length !== 1 ? "s" : ""}
          </Badge>
          <CardMenu
            queryId={query.id}
            queryName={query.name}
            isActive={query.is_active}
            onEdit={() => onEdit(query.id)}
            onScrapeNow={handleScrapeNow}
            onDelete={() => onDelete(query.id)}
          />
        </div>
      </div>

      <CardContent className="pt-4">
        {/* Price section */}
        {detailLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ) : lowestPrice !== null && lowestResult ? (
          <div className="space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="font-heading text-3xl font-bold">
                {formatPrice(lowestPrice)}
              </span>
              <span className={cn("text-sm font-medium", deltaColor(lowestResult.direction))}>
                {deltaIcon(lowestResult.direction)}{" "}
                {lowestResult.direction === "lower"
                  ? `-${lowestResult.pct_change.toFixed(1)}%`
                  : lowestResult.direction === "higher"
                    ? `+${lowestResult.pct_change.toFixed(1)}%`
                    : `${lowestResult.pct_change.toFixed(1)}%`}
              </span>
            </div>
            {breached && (
              <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                Below threshold
              </Badge>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            <span className="font-heading text-3xl font-bold text-muted-foreground">
              --
            </span>
          </div>
        )}

        {/* Threshold line */}
        <p className="mt-3 text-sm text-muted-foreground">
          Threshold: {formatPrice(query.threshold_cents)}
        </p>

        {/* Status line */}
        <div className="mt-2 flex items-center gap-2">
          <StatusDot status={status} />
          {latestScrapedAt && (
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(latestScrapedAt)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
