import { clsx } from "../lib/utils";

export function ProgressBar({ value = 0, color = "primary", className }) {
  const colorMap = {
    primary: "bg-indigo-500",
    success: "bg-emerald-500",
    danger: "bg-red-500",
    warning: "bg-amber-500",
  };

  return (
    <div
      className={clsx(
        "h-1.5 w-full rounded-full bg-[var(--color-border)]",
        className,
      )}
    >
      <div
        className={clsx(
          "h-full rounded-full transition-all duration-500",
          colorMap[color],
        )}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
