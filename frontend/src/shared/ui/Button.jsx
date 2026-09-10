import { clsx } from "../lib/utils";
import { Spinner } from "./Spinner";

const base =
  "inline-flex items-center justify-center gap-2 cursor-pointer whitespace-nowrap " +
  "rounded-[var(--taro-radius-control)] border " +
  "font-[family-name:var(--taro-font-body)] " +
  "transition-[background-color,border-color,color,transform,box-shadow] duration-[250ms] " +
  "disabled:cursor-not-allowed disabled:opacity-45 " +
  "disabled:hover:translate-y-0 disabled:hover:shadow-none";

const variants = {
  primary:
    "border-transparent bg-[var(--taro-brass)] text-[var(--taro-brass-ink)] font-semibold " +
    "hover:-translate-y-0.5 hover:shadow-[0_14px_30px_-14px_var(--taro-brass)]",
  secondary:
    "bg-transparent text-[var(--taro-ink)] font-medium " +
    "border-[var(--taro-line-quiet)] hover:border-[var(--taro-line-hover)]",
  ghost:
    "border-transparent bg-transparent text-[var(--taro-ink-muted)] font-medium " +
    "hover:text-[var(--taro-ink)]",
  danger:
    "bg-transparent text-[var(--taro-incorrect-ink)] font-medium " +
    "border-[var(--taro-incorrect-line)] " +
    "hover:border-[var(--taro-incorrect)] hover:bg-[var(--taro-incorrect-bg)]",
  github:
    "border-transparent bg-[var(--taro-ink)] text-[var(--taro-brass-ink)] font-semibold " +
    "hover:-translate-y-0.5",
};

const sizes = {
  sm: "px-[14px] py-[9px] text-[13px]",
  md: "px-[20px] py-[13px] text-[13.5px]",
  lg: "px-[22px] py-[14px] text-[14px]",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  loading,
  disabled,
  ...props
}) {
  return (
    <button
      className={clsx(base, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
