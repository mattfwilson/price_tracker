import { useState } from "react";
import { ArrowUp, ArrowDown } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { HealthStatusDot } from "./HealthStatusDot";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { UrlHealthResponse } from "@/types/api";

type SortColumn = "status" | "query" | "lastSuccess";
type SortDirection = "asc" | "desc";

// Higher value = worse status. With desc direction, worst (failing) appears first.
const STATUS_ORDER: Record<string, number> = {
  healthy: 0,
  degraded: 1,
  failing: 2,
};

interface HealthTableProps {
  urls: UrlHealthResponse[];
}

export function HealthTable({ urls }: HealthTableProps) {
  const [sort, setSort] = useState<{ column: SortColumn; direction: SortDirection }>({
    column: "status",
    direction: "desc",
  });

  function handleColumnClick(column: SortColumn) {
    setSort((prev) => {
      if (prev.column === column) {
        return { column, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { column, direction: "asc" };
    });
  }

  const sorted = [...urls].sort((a, b) => {
    const dir = sort.direction === "asc" ? 1 : -1;

    if (sort.column === "status") {
      const aOrder = STATUS_ORDER[a.status] ?? 3;
      const bOrder = STATUS_ORDER[b.status] ?? 3;
      return (aOrder - bOrder) * dir;
    }

    if (sort.column === "query") {
      return a.watch_query_name.localeCompare(b.watch_query_name) * dir;
    }

    if (sort.column === "lastSuccess") {
      if (a.last_success_at === null && b.last_success_at === null) return 0;
      if (a.last_success_at === null) return 1; // nulls always last
      if (b.last_success_at === null) return -1;
      const aTime = new Date(a.last_success_at).getTime();
      const bTime = new Date(b.last_success_at).getTime();
      return (aTime - bTime) * dir;
    }

    return 0;
  });

  function SortIcon({ column }: { column: SortColumn }) {
    if (sort.column !== column) return null;
    return sort.direction === "asc" ? (
      <ArrowUp className="ml-1 inline h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 inline h-3 w-3" />
    );
  }

  function headerClass(column: SortColumn) {
    return cn(
      "cursor-pointer select-none",
      sort.column === column ? "text-foreground" : "text-muted-foreground"
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead
            className={cn("w-10", headerClass("status"))}
            onClick={() => handleColumnClick("status")}
          >
            Status
            <SortIcon column="status" />
          </TableHead>
          <TableHead>URL</TableHead>
          <TableHead
            className={headerClass("query")}
            onClick={() => handleColumnClick("query")}
          >
            Watch Query
            <SortIcon column="query" />
          </TableHead>
          <TableHead className="w-20">Rate</TableHead>
          <TableHead
            className={cn("w-28", headerClass("lastSuccess"))}
            onClick={() => handleColumnClick("lastSuccess")}
          >
            Last Success
            <SortIcon column="lastSuccess" />
          </TableHead>
          <TableHead className="w-16">Fails</TableHead>
          <TableHead>Last Error</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((url) => (
          <TableRow key={url.retailer_url_id} className="hover:bg-accent">
            <TableCell>
              <HealthStatusDot status={url.status} />
            </TableCell>
            <TableCell>{url.domain}</TableCell>
            <TableCell className="max-w-[200px] truncate">
              {url.watch_query_name}
            </TableCell>
            <TableCell>
              {url.success_count}/{url.window_size}
            </TableCell>
            <TableCell>
              {url.last_success_at
                ? formatRelativeTime(url.last_success_at)
                : "--"}
            </TableCell>
            <TableCell>{url.consecutive_failures}</TableCell>
            <TableCell>{url.last_error_type ?? "--"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
