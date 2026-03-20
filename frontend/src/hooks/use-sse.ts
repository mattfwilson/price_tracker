import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/hooks/use-watch-queries";
import { formatPrice } from "@/lib/format";
import { toast } from "sonner";
import type { AlertSSEPayload } from "@/types/api";

export function useAlertSSE() {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      const es = new EventSource("http://localhost:8000/alerts/stream");
      eventSourceRef.current = es;

      es.addEventListener("alert", (event: MessageEvent) => {
        const data: AlertSSEPayload = JSON.parse(event.data);

        // Update unread count cache
        queryClient.setQueryData(queryKeys.unreadCount, {
          unread_count: data.unread_count,
        });

        // Invalidate alerts list
        queryClient.invalidateQueries({ queryKey: queryKeys.alerts });

        // Show toast notification
        toast(
          `${data.watch_query_name} — ${formatPrice(data.price_cents)} at ${data.retailer_name}`,
          { description: "Below threshold!", duration: 5000 }
        );
      });

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    }

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [queryClient]);
}
