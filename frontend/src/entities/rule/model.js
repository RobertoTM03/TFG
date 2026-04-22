export function truncateRule(text, max = 120) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}
