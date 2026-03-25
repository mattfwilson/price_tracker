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

export function formatChartDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Short date for wayback stats: "Mar 12" */
export const formatShortDate = formatChartDate;

export function formatScheduleLabel(schedule: string): string {
  switch (schedule) {
    case "daily": return "Daily";
    case "weekly": return "Weekly";
    case "every_1h": return "Every 1h";
    case "every_3h": return "Every 3h";
    case "every_6h": return "Every 6h";
    case "every_12h": return "Every 12h";
    default: return schedule;
  }
}

export function formatTimeUntil(isoString: string): string {
  const diff = new Date(isoString).getTime() - Date.now();
  if (diff <= 0) return "soon";
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.floor(hours / 24)}d`;
}
