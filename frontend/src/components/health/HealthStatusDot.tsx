import { cn } from "@/lib/utils";
import type { HealthStatus } from "@/types/api";

const healthConfig: Record<HealthStatus, { color: string; label: string }> = {
  healthy: { color: "bg-emerald-500", label: "Healthy" },
  degraded: { color: "bg-amber-500", label: "Degraded" },
  failing: { color: "bg-red-500", label: "Failing" },
};

interface HealthStatusDotProps {
  status: HealthStatus;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function HealthStatusDot({
  status,
  showLabel = false,
  size = "md",
}: HealthStatusDotProps) {
  const config = healthConfig[status];
  const dotSize = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn(dotSize, "rounded-full", config.color)} />
      {showLabel && (
        <span className="text-sm text-muted-foreground">{config.label}</span>
      )}
    </span>
  );
}
