export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      {icon && (
        <div className="mb-1 text-5xl text-[var(--taro-ink-dim)]">
          {icon}
        </div>
      )}
      <p className="font-[family-name:var(--taro-font-display)] text-[21px] font-semibold tracking-[-0.4px] text-[var(--taro-ink)]">{title}</p>
      {description && (
        <p className="max-w-sm text-[14px] leading-[1.6] text-[var(--taro-ink-muted)] [text-wrap:pretty]">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
