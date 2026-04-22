import { clsx } from "../lib/utils";

export function Input({ className, error, label, hint, ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-[var(--color-text)]">
          {label}
        </label>
      )}
      <input
        className={clsx(
          "w-full rounded-lg border bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] outline-none transition-colors",
          error
            ? "border-red-500/60 focus:border-red-500"
            : "border-[var(--color-border)] focus:border-indigo-500",
          className,
        )}
        {...props}
      />
      {hint && !error && (
        <p className="text-xs text-[var(--color-text-muted)]">{hint}</p>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

export function Textarea({ className, error, label, hint, ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-[var(--color-text)]">
          {label}
        </label>
      )}
      <textarea
        className={clsx(
          "w-full rounded-lg border bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] outline-none transition-colors resize-none",
          error
            ? "border-red-500/60 focus:border-red-500"
            : "border-[var(--color-border)] focus:border-indigo-500",
          className,
        )}
        {...props}
      />
      {hint && !error && (
        <p className="text-xs text-[var(--color-text-muted)]">{hint}</p>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
