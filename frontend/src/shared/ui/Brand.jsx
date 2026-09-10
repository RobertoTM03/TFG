import { clsx } from "../lib/utils";

export function Wordmark({ className }) {
  return (
    <span
      className={clsx(
        "font-[family-name:var(--taro-font-mono)] text-[15px] font-medium lowercase tracking-normal text-[var(--taro-ink)]",
        className,
      )}
    >
      ta<span className="text-[var(--taro-brass)]">r</span>o
    </span>
  );
}

export function BrandBadge({ size = 28, className }) {
  // Rampa del manual: bajo 24px la regla adelgaza y el radio se cierra.
  const t = Math.round(size * 0.5);
  const bar = Math.round(size * 0.47);
  const rule = size >= 24 ? 2 : 1;
  const gap = size >= 64 ? 9 : size >= 40 ? 5 : size >= 24 ? 3 : 2;
  const radius = size >= 64 ? 20 : size >= 40 ? 12 : size >= 24 ? 8 : 5;

  return (
    <span
      style={{ width: size, height: size, gap, borderRadius: radius }}
      className={clsx(
        "inline-flex shrink-0 flex-col items-center justify-center",
        "border border-[var(--taro-line-brass)] bg-[var(--taro-inset)]",
        className,
      )}
    >
      <span
        style={{ fontSize: t, lineHeight: 1 }}
        className="font-[family-name:var(--taro-font-display)] font-semibold text-[var(--taro-brass)]"
      >
        T
      </span>
      <span
        style={{ width: bar, height: rule }}
        className="block bg-[var(--taro-brass)]"
      />
    </span>
  );
}

export function BrandLockup({ className }) {
  return (
    <span className={clsx("inline-flex items-center gap-2.5", className)}>
      <BrandBadge />
      <Wordmark />
    </span>
  );
}
