import { clsx } from "../lib/utils";

export function Card({
  as,
  interactive = false,
  accent,
  flush = false,
  className,
  style,
  children,
  ...props
}) {
  const Tag = as ?? "div";

  return (
    <Tag
      style={{ ...(accent ? { borderColor: `var(${accent})` } : null), ...style }}
      className={clsx(
        "rounded-[var(--taro-radius-card)] border border-[var(--taro-line)] bg-[var(--taro-surface)]",
        !flush && "px-[26px] py-[28px]",
        interactive &&
          "cursor-pointer transition-[background-color,border-color,color] duration-[250ms] hover:bg-[var(--taro-raised)]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

// Columnas fijas a propósito: auto-fit deja una celda huérfana a anchos intermedios.
export function CardGrid({ columns = 2, className, children, ...props }) {
  return (
    <div
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      className={clsx(
        "grid gap-px overflow-hidden rounded-[var(--taro-radius-panel)] bg-[var(--taro-line)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardCell({ interactive = false, className, children, ...props }) {
  return (
    <div
      className={clsx(
        "bg-[var(--taro-surface)] px-[26px] py-[24px]",
        interactive &&
          "cursor-pointer transition-[background-color] duration-[250ms] hover:bg-[var(--taro-raised)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
