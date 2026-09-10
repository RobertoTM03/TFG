import { clsx } from "../lib/utils";

const labelClass =
  "font-[family-name:var(--taro-font-mono)] text-[11px] font-medium uppercase " +
  "tracking-[0.14em] text-[var(--taro-ink-dim)]";

const fieldClass =
  "w-full rounded-[var(--taro-radius-control)] border " +
  "bg-[var(--taro-raised)] px-[12px] py-[10px] " +
  "font-[family-name:var(--taro-font-body)] text-[13.5px] text-[var(--taro-ink)] " +
  "placeholder:text-[var(--taro-ink-dim)] " +
  "outline-none transition-[border-color] duration-[250ms] " +
  "disabled:cursor-not-allowed disabled:text-[var(--taro-ink-faint)]";

function borderClass(error) {
  return error
    ? "border-[var(--taro-incorrect-line)] focus:border-[var(--taro-incorrect)]"
    : "border-[var(--taro-line-strong)] focus:border-[var(--taro-brass)]";
}

function Field({ label, hint, error, children }) {
  return (
    <div className="flex flex-col gap-2">
      {label && <label className={labelClass}>{label}</label>}
      {children}
      {(hint || error) && (
        <p
          className={clsx(
            "min-h-[18px] text-[12px] leading-[18px]",
            error
              ? "text-[var(--taro-incorrect-ink)]"
              : "text-[var(--taro-ink-dim)]",
          )}
        >
          {error || hint}
        </p>
      )}
    </div>
  );
}

export function Input({ className, error, label, hint, ...props }) {
  return (
    <Field label={label} hint={hint} error={error}>
      <input
        className={clsx(fieldClass, borderClass(error), className)}
        {...props}
      />
    </Field>
  );
}

export function Textarea({ className, error, label, hint, ...props }) {
  return (
    <Field label={label} hint={hint} error={error}>
      <textarea
        className={clsx(
          fieldClass,
          borderClass(error),
          "resize-none leading-[1.6]",
          className,
        )}
        {...props}
      />
    </Field>
  );
}
