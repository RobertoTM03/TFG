import { clsx } from "../lib/utils";

export function Eyebrow({ as, className, children, ...props }) {
  const Tag = as ?? "span";
  return (
    <Tag
      className={clsx(
        "font-[family-name:var(--taro-font-mono)] text-[11px] font-medium uppercase",
        "tracking-[0.14em] whitespace-nowrap text-[var(--taro-ink-dim)]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function PageTitle({ className, children, ...props }) {
  return (
    <h1
      className={clsx(
        "font-[family-name:var(--taro-font-display)] text-[34px] font-semibold leading-[1.1]",
        "tracking-[-0.8px] text-[var(--taro-ink)]",
        className,
      )}
      {...props}
    >
      {children}
    </h1>
  );
}

export function SectionTitle({ as, className, children, ...props }) {
  const Tag = as ?? "h2";
  return (
    <Tag
      className={clsx(
        "font-[family-name:var(--taro-font-display)] text-[22px] font-semibold leading-[1.2]",
        "tracking-[-0.4px] text-[var(--taro-ink)]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function Body({ as, muted = false, className, children, ...props }) {
  const Tag = as ?? "p";
  return (
    <Tag
      className={clsx(
        "text-[14px] leading-[1.6] [text-wrap:pretty]",
        muted ? "text-[var(--taro-ink-muted)]" : "text-[var(--taro-ink)]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function Mono({ as, className, children, ...props }) {
  const Tag = as ?? "span";
  return (
    <Tag
      className={clsx(
        "font-[family-name:var(--taro-font-mono)] whitespace-nowrap",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function PageHeader({ eyebrow, title, action, className, children }) {
  return (
    <header
      className={clsx("flex items-start justify-between gap-6", className)}
    >
      <div className="min-w-0">
        {eyebrow && <Eyebrow className="block">{eyebrow}</Eyebrow>}
        <PageTitle className={eyebrow ? "mt-2" : undefined}>{title}</PageTitle>
        {children}
      </div>
      {action && <div className="shrink-0 pt-2">{action}</div>}
    </header>
  );
}

export function Tabs({ tabs, value, onChange, className }) {
  return (
    <div
      className={clsx(
        "flex gap-6 border-b border-[var(--taro-line)]",
        className,
      )}
      role="tablist"
    >
      {tabs.map((tab) => {
        const active = tab.value === value;
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.value)}
            className={clsx(
              "-mb-px cursor-pointer border-b-2 pb-2.5 text-[14px] whitespace-nowrap",
              "transition-[color,border-color] duration-[250ms]",
              active
                ? "border-[var(--taro-brass)] text-[var(--taro-ink)]"
                : "border-transparent text-[var(--taro-ink-dim)] hover:text-[var(--taro-ink)]",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
