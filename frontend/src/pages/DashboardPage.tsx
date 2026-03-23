import { useMemo, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useWatchQueries, useWatchQueryDetail, queryKeys } from "@/hooks/use-watch-queries";
import { useHealthUrls } from "@/hooks/use-health";
import { QueryCardGrid } from "@/components/dashboard/QueryCardGrid";
import { QueryFormDialog } from "@/components/query/QueryFormDialog";
import { DeleteQueryDialog } from "@/components/query/DeleteQueryDialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { UrlHealthResponse } from "@/types/api";

export function DashboardPage() {
  const { data: queries, isLoading, isError } = useWatchQueries();
  const { data: allHealthData } = useHealthUrls();
  const queryClient = useQueryClient();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editQueryId, setEditQueryId] = useState<number | null>(null);
  const [deleteQuery, setDeleteQuery] = useState<{ id: number; name: string } | null>(null);
  const [isScrapingAll, setIsScrappingAll] = useState(false);

  const { data: editQueryDetail } = useWatchQueryDetail(editQueryId);

  const healthByQuery = useMemo(() => {
    if (!allHealthData) return {};
    const map: Record<number, UrlHealthResponse[]> = {};
    for (const h of allHealthData) {
      (map[h.watch_query_id] ??= []).push(h);
    }
    return map;
  }, [allHealthData]);

  const activeQueries = queries?.filter((q) => q.is_active) ?? [];

  async function handleScrapeAll() {
    if (activeQueries.length === 0) return;
    setIsScrappingAll(true);
    try {
      await Promise.allSettled(activeQueries.map((q) => api.watchQueries.scrape(q.id)));
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
      toast(`Scrape started for ${activeQueries.length} quer${activeQueries.length === 1 ? "y" : "ies"}`);
    } finally {
      setIsScrappingAll(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">Dashboard</h1>
        {!isLoading && !isError && activeQueries.length > 0 && (
          <Button
            variant="default"
            size="sm"
            onClick={handleScrapeAll}
            disabled={isScrapingAll}
          >
            {isScrapingAll ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Scrape All
          </Button>
        )}
      </div>

      <QueryCardGrid
        queries={queries}
        isLoading={isLoading}
        isError={isError}
        onCardClick={(id) => setEditQueryId(id)}
        onNewQuery={() => setShowCreateDialog(true)}
        onEdit={(id) => setEditQueryId(id)}
        onDelete={(id) => {
          const query = queries?.find((q) => q.id === id);
          setDeleteQuery({ id, name: query?.name ?? "" });
        }}
        healthByQuery={healthByQuery}
      />

      <QueryFormDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />

      <QueryFormDialog
        open={editQueryId !== null}
        onOpenChange={(open) => {
          if (!open) setEditQueryId(null);
        }}
        editQuery={editQueryDetail}
      />

      <DeleteQueryDialog
        open={deleteQuery !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteQuery(null);
        }}
        queryId={deleteQuery?.id ?? null}
        queryName={deleteQuery?.name ?? ""}
      />
    </div>
  );
}
