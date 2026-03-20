import { useState } from "react";
import { useWatchQueries, useWatchQueryDetail } from "@/hooks/use-watch-queries";
import { QueryCardGrid } from "@/components/dashboard/QueryCardGrid";
import { QueryFormDialog } from "@/components/query/QueryFormDialog";
import { DeleteQueryDialog } from "@/components/query/DeleteQueryDialog";

export function DashboardPage() {
  const { data: queries, isLoading, isError } = useWatchQueries();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editQueryId, setEditQueryId] = useState<number | null>(null);
  const [deleteQuery, setDeleteQuery] = useState<{ id: number; name: string } | null>(null);

  const { data: editQueryDetail } = useWatchQueryDetail(editQueryId);

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold mb-6">Dashboard</h1>

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
