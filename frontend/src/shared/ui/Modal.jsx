import { useEffect } from "react";

export function Modal({ open, onClose, title, children, footer }) {
  useEffect(() => {
    if (!open) return;
    const handler = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-[var(--taro-scrim)]"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-lg rounded-[var(--taro-radius-panel)] border border-[var(--taro-line)] bg-[var(--taro-surface)]">
        <div className="flex items-center justify-between border-b border-[var(--taro-line)] px-6 py-5">
          <h2 className="font-[family-name:var(--taro-font-display)] text-[21px] font-semibold tracking-[-0.4px] text-[var(--taro-ink)]">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="cursor-pointer text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-ink)]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer && (
          <div className="flex justify-end gap-3 border-t border-[var(--taro-line)] px-6 py-5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
