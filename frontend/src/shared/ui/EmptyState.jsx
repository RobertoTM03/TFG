export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      {icon && (
        <div className="text-[var(--color-text-muted)] text-5xl mb-1">
          {icon}
        </div>
      )}
      <p className="text-base font-medium text-[var(--color-text)]">{title}</p>
      {description && (
        <p className="text-sm text-[var(--color-text-muted)] max-w-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
