import { clsx } from "../lib/utils";

const variants = {
  primary:
    "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white border-transparent",
  secondary:
    "bg-transparent hover:bg-[#1a1a1a] text-[var(--color-text)] border-[rgba(255,255,255,0.15)]",
  danger: "bg-transparent hover:bg-red-950/40 text-red-400 border-red-900/50",
  ghost:
    "bg-transparent hover:bg-[#111] text-[var(--color-text-muted)] border-transparent",
  github: "bg-[#f5f5f5] hover:bg-white text-[#111] border-transparent gap-2",
};

const sizes = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-3.5 py-1.5 text-sm",
  lg: "px-5 py-2.5 text-sm",
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
      className={clsx(
        "inline-flex items-center justify-center font-medium rounded-md border transition-colors duration-100 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin -ml-0.5 mr-2 h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
