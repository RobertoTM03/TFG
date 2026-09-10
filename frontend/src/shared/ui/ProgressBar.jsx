import { clsx } from "../lib/utils";

export function ProgressBar({ value = 0, className }) {
  const pct = Math.min(100, Math.max(0, value));

  return (
    <div
      className={clsx(
        "h-[4px] w-full overflow-hidden rounded-[var(--taro-radius-control)] bg-[var(--taro-line)]",
        className,
      )}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-[var(--taro-radius-control)] bg-[var(--taro-brass)]"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
