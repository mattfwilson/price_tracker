import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useWatchQueryDetail } from "@/hooks/use-watch-queries";
import { formatPrice } from "@/lib/format";
import { ListingRow } from "./ListingRow";
import type { RetailerUrlWithLatest } from "@/types/api";

interface QuerySheetProps {
  queryId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function findLowestPriceUrlId(
  urls: RetailerUrlWithLatest[]
): number | null {
  let lowestId: number | null = null;
  let lowestPrice = Infinity;
  for (const url of urls) {
    if (url.latest_result && url.latest_result.price_cents < lowestPrice) {
      lowestPrice = url.latest_result.price_cents;
      lowestId = url.id;
    }
  }
  return lowestId;
}

export function QuerySheet({ queryId, open, onOpenChange }: QuerySheetProps) {
  const { data: detail, isLoading } = useWatchQueryDetail(queryId);

  const lowestPriceUrlId = detail
    ? findLowestPriceUrlId(detail.retailer_urls)
    : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:w-[480px] sm:max-w-[480px]"
      >
        {isLoading && (
          <>
            <SheetHeader>
              <SheetTitle>
                <Skeleton className="h-6 w-48" />
              </SheetTitle>
              <SheetDescription>
                <Skeleton className="h-4 w-32" />
              </SheetDescription>
            </SheetHeader>
            <div className="mt-6 space-y-4">
              <Skeleton className="w-full h-16" />
              <Skeleton className="w-full h-16" />
              <Skeleton className="w-full h-16" />
            </div>
          </>
        )}

        {detail && (
          <>
            <SheetHeader>
              <SheetTitle className="font-heading">{detail.name}</SheetTitle>
              <SheetDescription>
                Threshold: {formatPrice(detail.threshold_cents)}
              </SheetDescription>
            </SheetHeader>

            <div className="mt-6 overflow-y-auto flex-1">
              {detail.retailer_urls.length === 0 ? (
                <p className="text-sm text-muted-foreground">No listings yet</p>
              ) : (
                detail.retailer_urls.map((url, index) => (
                  <div key={url.id}>
                    <ListingRow
                      url={url}
                      isLowest={url.id === lowestPriceUrlId}
                      thresholdCents={detail.threshold_cents}
                    />
                    {index < detail.retailer_urls.length - 1 && <Separator />}
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
