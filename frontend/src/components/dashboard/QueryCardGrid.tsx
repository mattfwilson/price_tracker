import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { QueryCard } from "./QueryCard";
import { NewQueryCard } from "./NewQueryCard";
import type { WatchQueryResponse } from "@/types/api";

interface QueryCardGridProps {
  queries: WatchQueryResponse[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onCardClick: (id: number) => void;
  onNewQuery: () => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

function SkeletonCard() {
  return (
    <Card className="min-h-[200px] p-6 space-y-4">
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-10 w-20" />
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-4 w-24" />
    </Card>
  );
}

export function QueryCardGrid({
  queries,
  isLoading,
  isError,
  onCardClick,
  onNewQuery,
  onEdit,
  onDelete,
}: QueryCardGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState />;
  }

  if (queries?.length === 0) {
    return (
      <EmptyState
        heading="No watch queries yet"
        body="Create your first watch query to start tracking prices across retailers."
        action={{ label: "Add Query", onClick: onNewQuery }}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {queries?.map((query) => (
        <QueryCard
          key={query.id}
          query={query}
          onCardClick={onCardClick}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
      <NewQueryCard onClick={onNewQuery} />
    </div>
  );
}
