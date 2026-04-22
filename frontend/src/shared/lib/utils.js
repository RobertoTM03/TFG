export function formatDate(iso) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function formatDuration(start, end) {
  if (!start || !end) return "—";
  const ms = new Date(end) - new Date(start);
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export function verdictColor(verdict) {
  const map = { pass: "success", fail: "danger", partial: "partial" };
  return map[verdict] ?? "muted";
}

export function statusColor(status) {
  const map = {
    completed: "success",
    failed: "danger",
    running: "primary",
    pending: "warning",
  };
  return map[status] ?? "muted";
}

export function clsx(...classes) {
  return classes.filter(Boolean).join(" ");
}
