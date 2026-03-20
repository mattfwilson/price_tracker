import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import {
  useAlerts,
  useUnreadCount,
  useMarkAlertRead,
  useDismissAllAlerts,
} from "@/hooks/use-alerts";
import { formatPrice, formatRelativeTime } from "@/lib/format";

export function BellDropdown() {
  const { data: alerts } = useAlerts(10);
  const { data: unreadData } = useUnreadCount();
  const markRead = useMarkAlertRead();
  const dismissAll = useDismissAllAlerts();

  const unreadCount = unreadData?.unread_count ?? 0;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell size={20} />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[20px] h-5 rounded-full bg-destructive text-destructive-foreground text-xs font-bold flex items-center justify-center px-1">
              {unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80 max-h-[400px] overflow-y-auto p-0" align="end">
        <div className="font-heading text-sm font-bold p-3">
          {unreadCount > 0 ? `Alerts (${unreadCount} unread)` : "Alerts"}
        </div>

        <Separator />

        <div>
          {(!alerts || alerts.length === 0) ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No alerts
            </p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className="px-3 py-2 hover:bg-accent cursor-pointer flex items-start gap-2"
                onClick={() => {
                  if (!alert.is_read) {
                    markRead.mutate(alert.id);
                  }
                }}
              >
                <div className="mt-1.5 shrink-0">
                  {!alert.is_read ? (
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                  ) : (
                    <div className="w-2 h-2" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">
                    {alert.watch_query_name}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatPrice(alert.price_cents)} at {alert.retailer_name}
                  </div>
                </div>

                <div className="text-xs text-muted-foreground shrink-0">
                  {formatRelativeTime(alert.created_at)}
                </div>
              </div>
            ))
          )}
        </div>

        <Separator />

        <div className="flex justify-between items-center p-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={() => dismissAll.mutate()}
            disabled={dismissAll.isPending}
          >
            Dismiss All
          </Button>
          <Link to="/alerts" className="text-sm text-primary hover:underline">
            View All
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
