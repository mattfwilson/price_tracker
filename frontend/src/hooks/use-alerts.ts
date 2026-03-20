import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/hooks/use-watch-queries";

export function useAlerts(limit?: number) {
  return useQuery({
    queryKey: [...queryKeys.alerts, limit] as const,
    queryFn: () => api.alerts.list(limit),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: queryKeys.unreadCount,
    queryFn: api.alerts.unreadCount,
    refetchInterval: 30_000,
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.alerts.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
      queryClient.invalidateQueries({ queryKey: queryKeys.unreadCount });
    },
  });
}

export function useDismissAllAlerts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.alerts.dismissAll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
      queryClient.invalidateQueries({ queryKey: queryKeys.unreadCount });
    },
  });
}
