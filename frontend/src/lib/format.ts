export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export function deltaIcon(direction: string): string {
  switch (direction) {
    case "higher":
      return "\u2191"; // up arrow
    case "lower":
      return "\u2193"; // down arrow
    default:
      return "\u2014"; // em dash
  }
}

export function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) return "just now";

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;

  return new Date(isoString).toLocaleDateString();
}

export function formatDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const SCHEDULE_LABELS: Record<string, string> = {
  every_1h: "Every 1h",
  every_3h: "Every 3h",
  every_6h: "Every 6h",
  every_12h: "Every 12h",
  daily: "Daily",
  weekly: "Weekly",
};

export function formatScheduleLabel(schedule: string): string {
  return SCHEDULE_LABELS[schedule] ?? schedule;
}

export function formatTimeUntil(isoString: string): string {
  const diffSeconds = Math.floor((new Date(isoString).getTime() - Date.now()) / 1000);
  if (diffSeconds <= 0) return "soon";

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `in ${diffMinutes}m`;

  const diffHours = Math.floor(diffMinutes / 60);
  const remMinutes = diffMinutes % 60;
  if (diffHours < 24) return remMinutes > 0 ? `in ${diffHours}h ${remMinutes}m` : `in ${diffHours}h`;

  const diffDays = Math.floor(diffHours / 24);
  return `in ${diffDays}d`;
}

export function formatChartDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
