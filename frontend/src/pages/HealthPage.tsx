import { useState } from "react";
import {
  Table,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { HealthFilter } from "@/components/health/HealthFilter";
import { HealthTable } from "@/components/health/HealthTable";
import { useHealthUrls } from "@/hooks/use-health";

function SkeletonRows() {
  return (
    <Table>
      <TableBody>
        {Array.from({ length: 5 }).map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <Skeleton className="h-2.5 w-2.5 rounded-full" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-28" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-32" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-12" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-20" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-8" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-24" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function HealthPage() {
  const { data: urls, isLoading, isError } = useHealthUrls();
  const [filter, setFilter] = useState<"all" | "problems">("all");

  const filtered =
    filter === "problems"
      ? (urls ?? []).filter((u) => u.status !== "healthy")
      : (urls ?? []);

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold mb-6">Scrape Health</h1>
      <HealthFilter mode={filter} onChange={setFilter} />
      {isLoading ? (
        <SkeletonRows />
      ) : isError ? (
        <ErrorState />
      ) : !urls || urls.length === 0 ? (
        <EmptyState
          heading="No URLs tracked"
          body="Add retailer URLs to your watch queries to see their health status here."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          heading="No URLs tracked"
          body="No degraded or failing URLs found."
        />
      ) : (
        <HealthTable urls={filtered} />
      )}
    </div>
  );
}
