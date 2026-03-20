import { useState } from "react";
import { useWatchQueries } from "@/hooks/use-watch-queries";
import { QueryCardGrid } from "@/components/dashboard/QueryCardGrid";

export function DashboardPage() {
  const { data: queries, isLoading, isError } = useWatchQueries();

  // State for slide-over (Plan 03 will add QuerySheet)
  const [_selectedQueryId, setSelectedQueryId] = useState<number | null>(null);

  // State for create dialog (Plan 03 will add QueryFormDialog)
  const [_showCreateDialog, setShowCreateDialog] = useState(false);

  // State for edit dialog (Plan 03 will add QueryFormDialog in edit mode)
  const [_editQueryId, setEditQueryId] = useState<number | null>(null);

  // State for delete confirmation (Plan 03 will add AlertDialog)
  const [_deleteQueryId, setDeleteQueryId] = useState<number | null>(null);

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold mb-6">Dashboard</h1>

      <QueryCardGrid
        queries={queries}
        isLoading={isLoading}
        isError={isError}
        onCardClick={(id) => setSelectedQueryId(id)}
        onNewQuery={() => setShowCreateDialog(true)}
        onEdit={(id) => setEditQueryId(id)}
        onDelete={(id) => setDeleteQueryId(id)}
      />

      {/* TODO: Plan 03 — QuerySheet slide-over for selectedQueryId */}
      {/* TODO: Plan 03 — QueryFormDialog for showCreateDialog */}
      {/* TODO: Plan 03 — QueryFormDialog (edit mode) for editQueryId */}
      {/* TODO: Plan 03 — AlertDialog delete confirmation for deleteQueryId */}
    </div>
  );
}
