import type { HistoryRecord } from "@/types/api";

export type TimeRange = "7d" | "30d" | "90d" | "all";

const ranges: { value: TimeRange; label: string }[] = [
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "90d", label: "90d" },
  { value: "all", label: "All" },
];

interface TimeRangeFilterProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function filterByRange(
  records: HistoryRecord[],
  range: TimeRange,
): HistoryRecord[] {
  if (range === "all") return records;
  const days = { "7d": 7, "30d": 30, "90d": 90 }[range];
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return records.filter((r) => new Date(r.scraped_at) >= cutoff);
}

export function TimeRangeFilter({ value, onChange }: TimeRangeFilterProps) {
  return (
    <div className="flex items-center gap-1">
      {ranges.map((r) => (
        <button
          key={r.value}
          onClick={() => onChange(r.value)}
          className={`min-w-[44px] px-3 py-1 text-xs uppercase tracking-wide font-body rounded-md transition-colors ${
            value === r.value
              ? "bg-primary text-primary-foreground"
              : "bg-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
