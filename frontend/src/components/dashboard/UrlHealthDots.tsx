import { HealthStatusDot } from "@/components/health/HealthStatusDot";
import { formatRelativeTime } from "@/lib/format";
import type { UrlHealthResponse } from "@/types/api";

interface UrlHealthDotsProps {
  healthData: UrlHealthResponse[] | undefined;
}

export function UrlHealthDots({ healthData }: UrlHealthDotsProps) {
  if (!healthData || healthData.length === 0) return null;

  return (
    <div className="mt-2 flex flex-col gap-1">
      {healthData.map((h) => {
        const lastSuccess = h.last_success_at
          ? formatRelativeTime(h.last_success_at)
          : "never";
        const tooltip = `${h.domain} \u00b7 ${h.success_count}/${h.window_size} \u00b7 last success ${lastSuccess}`;

        return (
          <div
            key={h.retailer_url_id}
            className="flex items-center gap-2"
            title={tooltip}
          >
            <HealthStatusDot status={h.status} size="sm" />
            <span className="text-xs text-muted-foreground">{h.domain}</span>
          </div>
        );
      })}
    </div>
  );
}
