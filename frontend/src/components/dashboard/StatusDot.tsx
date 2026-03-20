import { cn } from "@/lib/utils";
import type { WatchQueryDetailResponse } from "@/types/api";

export type StatusType = "ok" | "error" | "running" | "paused";

const statusConfig: Record<
  StatusType,
  { color: string; label: string; pulse?: boolean }
> = {
  ok: { color: "bg-emerald-500", label: "OK" },
  error: { color: "bg-red-500", label: "Error" },
  running: { color: "bg-amber-500", label: "Running", pulse: true },
  paused: { color: "bg-zinc-400", label: "Paused" },
};

interface StatusDotProps {
  status: StatusType;
}

export function StatusDot({ status }: StatusDotProps) {
  const config = statusConfig[status];
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          "h-2.5 w-2.5 rounded-full",
          config.color,
          config.pulse && "animate-pulse"
        )}
      />
      <span className="text-sm text-muted-foreground">{config.label}</span>
    </span>
  );
}

export function deriveStatus(
  detail: WatchQueryDetailResponse | undefined,
  isScrapingLocal: boolean
): StatusType {
  if (isScrapingLocal) return "running";
  if (detail && !detail.is_active) return "paused";
  return "ok";
}
