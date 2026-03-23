import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export const healthKeys = {
  urls: ["scrape-health", "urls"] as const,
  byQuery: (id: number) => ["scrape-health", "query", id] as const,
};

export function useHealthUrls() {
  return useQuery({
    queryKey: healthKeys.urls,
    queryFn: api.scrapeHealth.urls,
    select: (data) => data.urls,
  });
}

export function useHealthByQuery(watchQueryId: number | null) {
  return useQuery({
    queryKey: healthKeys.byQuery(watchQueryId!),
    queryFn: () => api.scrapeHealth.byQuery(watchQueryId!),
    enabled: watchQueryId !== null,
    select: (data) => data.urls,
  });
}
