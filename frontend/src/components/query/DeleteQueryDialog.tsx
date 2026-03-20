import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDeleteWatchQuery } from "@/hooks/use-watch-queries";

interface DeleteQueryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  queryId: number | null;
  queryName: string;
}

export function DeleteQueryDialog({
  open,
  onOpenChange,
  queryId,
  queryName,
}: DeleteQueryDialogProps) {
  const deleteMutation = useDeleteWatchQuery();

  async function handleDelete() {
    if (queryId === null) return;
    try {
      await deleteMutation.mutateAsync(queryId);
      onOpenChange(false);
    } catch {
      // Error handled by TanStack Query
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {queryName}?</AlertDialogTitle>
          <AlertDialogDescription>
            This will permanently remove this watch query, all its retailer
            URLs, and scrape history. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep Query</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={handleDelete}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
