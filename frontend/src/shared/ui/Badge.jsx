import { clsx } from "../lib/utils";

const colorMap = {
  success: "bg-emerald-950/60 text-emerald-400 border-emerald-800/50",
  danger: "bg-red-950/60 text-red-400 border-red-800/50",
  warning: "bg-amber-950/60 text-amber-400 border-amber-800/50",
  primary: "bg-blue-950/60 text-blue-400 border-blue-800/50",
  partial: "bg-orange-950/60 text-orange-400 border-orange-800/50",
  muted:
    "bg-[#111] text-[var(--color-text-muted)] border-[rgba(255,255,255,0.1)]",
};

export function Badge({ children, color = "muted", className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded border",
        colorMap[color],
        className,
      )}
    >
      {children}
    </span>
  );
}
