import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useListingHistory } from "@/hooks/use-watch-queries";
import { formatChartDate } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PriceChart } from "./PriceChart";
import { PriceTable } from "./PriceTable";
import {
  TimeRangeFilter,
  filterByRange,
  type TimeRange,
} from "./TimeRangeFilter";

interface PriceHistoryViewProps {
  retailerUrlId: number;
  thresholdCents: number;
  productName: string;
  retailerDomain: string;
  onBack: () => void;
}

export function PriceHistoryView({
  retailerUrlId,
  thresholdCents,
  productName,
  retailerDomain,
  onBack,
}: PriceHistoryViewProps) {
  const { data, isLoading, isError, refetch } =
    useListingHistory(retailerUrlId);
  const [range, setRange] = useState<TimeRange>("30d");

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-[300px] w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16">
        <h2 className="font-heading text-lg font-semibold">
          Couldn't load history
        </h2>
        <p className="text-sm text-muted-foreground">
          Check your connection and try again.
        </p>
        <Button variant="ghost" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="flex flex-col items-center justify-center gap-2 py-16">
          <h2 className="font-heading text-lg font-semibold">
            No history yet
          </h2>
          <p className="text-sm text-muted-foreground">
            Trigger a scrape to start tracking price changes.
          </p>
        </div>
      </div>
    );
  }

  const filtered = filterByRange(data, range);
  // Sort chronologically (oldest first) for chart line rendering
  const chronological = Array.from(filtered).sort(
    (a, b) =>
      new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime(),
  );
  const chartData = chronological.map((r) => ({
    date: formatChartDate(r.scraped_at),
    price: r.price_cents / 100,
    scraped_at: r.scraped_at,
  }));
  const thresholdDollars = thresholdCents > 0 ? thresholdCents / 100 : null;

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      <h2 className="font-heading text-lg font-semibold truncate">
        {productName} &middot; {retailerDomain}
      </h2>

      <TimeRangeFilter value={range} onChange={setRange} />

      <div className="mt-2">
        <PriceChart data={chartData} thresholdDollars={thresholdDollars} />
      </div>

      <div className="mt-0">
        <PriceTable data={filtered} />
      </div>
    </div>
  );
}
