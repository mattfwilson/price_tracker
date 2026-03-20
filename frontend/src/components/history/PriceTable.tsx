import { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatDate } from "@/lib/format";
import type { HistoryRecord } from "@/types/api";

type SortKey = "scraped_at" | "price_cents" | "pct_change";
type SortDir = "asc" | "desc";

interface PriceTableProps {
  data: HistoryRecord[];
}

function sortRecords(
  records: HistoryRecord[],
  key: SortKey,
  dir: SortDir,
): HistoryRecord[] {
  return Array.from(records).sort((a, b) => {
    let cmp: number;
    if (key === "scraped_at") {
      cmp =
        new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime();
    } else {
      cmp = a[key] - b[key];
    }
    return dir === "asc" ? cmp : -cmp;
  });
}

const defaultDirs: Record<SortKey, SortDir> = {
  scraped_at: "desc",
  price_cents: "asc",
  pct_change: "asc",
};

export function PriceTable({ data }: PriceTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("scraped_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(defaultDirs[key]);
    }
  }

  function SortIcon({ column }: { column: SortKey }) {
    if (column !== sortKey) {
      return <ArrowUpDown className="inline h-3.5 w-3.5 text-muted-foreground" />;
    }
    return sortDir === "asc" ? (
      <ArrowUp className="inline h-3.5 w-3.5 text-foreground" />
    ) : (
      <ArrowDown className="inline h-3.5 w-3.5 text-foreground" />
    );
  }

  const sorted = sortRecords(data, sortKey, sortDir);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead
            className="cursor-pointer text-xs uppercase tracking-wide hover:text-foreground py-2 px-3"
            onClick={() => handleSort("scraped_at")}
          >
            Date <SortIcon column="scraped_at" />
          </TableHead>
          <TableHead
            className="cursor-pointer text-xs uppercase tracking-wide hover:text-foreground py-2 px-3"
            onClick={() => handleSort("price_cents")}
          >
            Price <SortIcon column="price_cents" />
          </TableHead>
          <TableHead
            className="cursor-pointer text-xs uppercase tracking-wide hover:text-foreground py-2 px-3"
            onClick={() => handleSort("pct_change")}
          >
            Change <SortIcon column="pct_change" />
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((record) => (
          <TableRow key={record.id}>
            <TableCell className="py-2 px-3">
              {formatDate(record.scraped_at)}
            </TableCell>
            <TableCell className="py-2 px-3 font-[tabular-nums]">
              {formatPrice(record.price_cents)}
            </TableCell>
            <TableCell className="py-2 px-3">
              <DeltaCell record={record} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DeltaCell({ record }: { record: HistoryRecord }) {
  if (record.direction === "new") {
    return <Badge variant="secondary">New</Badge>;
  }

  const pct = Math.abs(record.pct_change).toFixed(1);

  if (record.direction === "lower") {
    return (
      <span className="text-emerald-400">
        {"\u2193"} -{pct}%
      </span>
    );
  }
  if (record.direction === "higher") {
    return (
      <span className="text-red-400">
        {"\u2191"} +{pct}%
      </span>
    );
  }
  // unchanged
  return (
    <span className="text-zinc-400">
      {"\u2014"} 0.0%
    </span>
  );
}
