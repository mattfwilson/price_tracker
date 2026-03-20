import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WatchQueryCreate, WatchQueryUpdate } from "@/types/api";

export const queryKeys = {
  watchQueries: ["watch-queries"] as const,
  watchQueryDetail: (id: number) => ["watch-queries", id] as const,
  alerts: ["alerts"] as const,
  unreadCount: ["alerts", "unread-count"] as const,
};

export function useWatchQueries() {
  return useQuery({
    queryKey: queryKeys.watchQueries,
    queryFn: api.watchQueries.list,
  });
}

export function useWatchQueryDetail(id: number | null) {
  return useQuery({
    queryKey: queryKeys.watchQueryDetail(id!),
    queryFn: () => api.watchQueries.detail(id!),
    enabled: id !== null,
  });
}

export function useCreateWatchQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WatchQueryCreate) => api.watchQueries.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
    },
  });
}

export function useUpdateWatchQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: WatchQueryUpdate }) =>
      api.watchQueries.update(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
      queryClient.invalidateQueries({
        queryKey: queryKeys.watchQueryDetail(variables.id),
      });
    },
  });
}

export function useDeleteWatchQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.watchQueries.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
    },
  });
}

export function useScrapeNow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.watchQueries.scrape(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.watchQueryDetail(id),
      });
    },
  });
}

export function usePauseQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.watchQueries.pause(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
      queryClient.invalidateQueries({
        queryKey: queryKeys.watchQueryDetail(id),
      });
    },
  });
}

export function useResumeQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.watchQueries.resume(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
      queryClient.invalidateQueries({
        queryKey: queryKeys.watchQueryDetail(id),
      });
    },
  });
}
