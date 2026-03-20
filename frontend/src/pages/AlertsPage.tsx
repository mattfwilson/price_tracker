import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import {
  useAlerts,
  useMarkAlertRead,
  useDismissAllAlerts,
} from "@/hooks/use-alerts";
import { formatPrice, formatRelativeTime } from "@/lib/format";

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          <TableCell><Skeleton className="h-2 w-2 rounded-full" /></TableCell>
          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-12" /></TableCell>
        </TableRow>
      ))}
    </>
  );
}

export function AlertsPage() {
  const { data: alerts, isLoading } = useAlerts();
  const markRead = useMarkAlertRead();
  const dismissAll = useDismissAllAlerts();

  if (!isLoading && (!alerts || alerts.length === 0)) {
    return (
      <div>
        <div className="flex justify-between items-center mb-6">
          <h1 className="font-heading text-2xl font-bold">Alert Log</h1>
        </div>
        <EmptyState
          heading="No alerts yet"
          body="Alerts appear here when a tracked product drops to or below your price threshold."
        />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="font-heading text-2xl font-bold">Alert Log</h1>
        <Button
          variant="outline"
          className="text-destructive border-destructive"
          onClick={() => dismissAll.mutate()}
          disabled={dismissAll.isPending}
        >
          Dismiss All
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">Status</TableHead>
            <TableHead>Query Name</TableHead>
            <TableHead>Product</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Retailer</TableHead>
            <TableHead>Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <SkeletonRows />
          ) : (
            alerts?.map((alert) => (
              <TableRow
                key={alert.id}
                className="cursor-pointer hover:bg-accent"
                onClick={() => {
                  if (!alert.is_read) {
                    markRead.mutate(alert.id);
                  }
                }}
              >
                <TableCell>
                  {!alert.is_read && (
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                  )}
                </TableCell>
                <TableCell className="font-medium">
                  {alert.watch_query_name}
                </TableCell>
                <TableCell className="max-w-[200px] truncate">
                  {alert.product_name}
                </TableCell>
                <TableCell>{formatPrice(alert.price_cents)}</TableCell>
                <TableCell>{alert.retailer_name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatRelativeTime(alert.created_at)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
