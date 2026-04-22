import { useState } from "react";
import { deleteRule } from "@/entities/rule/api";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Modal } from "@/shared/ui/Modal";

export function RuleList({ rules, owner, repo, onDeleted }) {
  const [deleting, setDeleting] = useState(null);
  const [confirmId, setConfirmId] = useState(null);

  async function handleDelete(ruleId) {
    setDeleting(ruleId);
    try {
      await deleteRule(owner, repo, ruleId);
      onDeleted?.(ruleId);
    } finally {
      setDeleting(null);
      setConfirmId(null);
    }
  }

  if (!rules?.length) return null;

  return (
    <>
      <ol className="flex flex-col gap-2">
        {rules.map((rule, idx) => (
          <li
            key={rule.id}
            className="flex items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 group"
          >
            <span className="flex-shrink-0 mt-0.5 h-5 w-5 flex items-center justify-center rounded bg-indigo-600/20 text-xs font-bold text-indigo-400">
              {idx + 1}
            </span>
            <p className="flex-1 text-sm text-[var(--color-text)] leading-relaxed">
              {rule.rule_text}
            </p>
            <button
              onClick={() => setConfirmId(rule.id)}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-muted)] hover:text-red-400"
              title="Eliminar regla"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </li>
        ))}
      </ol>

      <Modal
        open={!!confirmId}
        onClose={() => setConfirmId(null)}
        title="Eliminar regla"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmId(null)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              loading={!!deleting}
              onClick={() => handleDelete(confirmId)}
            >
              Eliminar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-muted)]">
          ¿Estás seguro de que quieres eliminar esta regla? Esta acción no se
          puede deshacer.
        </p>
        {confirmId && (
          <div className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)]">
            {rules.find((r) => r.id === confirmId)?.rule_text}
          </div>
        )}
      </Modal>
    </>
  );
}
