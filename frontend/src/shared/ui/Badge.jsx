import { clsx } from "../lib/utils";
import { statusCss, statusLabel } from "../lib/status";

export function Badge({ kind = "tone", value = "neutral", color, children, className }) {
  const k = color ? "tone" : kind;
  const v = color ?? value;
  const { color: ink, background } = statusCss(k, v);

  return (
    <span
      style={{ color: ink, background }}
      className={clsx(
        "inline-flex items-center gap-1 whitespace-nowrap",
        "px-[10px] py-[4px] rounded-[var(--taro-radius-control)]",
        "font-[family-name:var(--taro-font-mono)] text-[11px] font-medium leading-none",
        className,
      )}
    >
      {children ?? statusLabel(k, v)}
    </span>
  );
}
