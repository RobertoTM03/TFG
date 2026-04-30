import { useRef, useState } from "react";
import { createRule, updateRule, deleteRule } from "@/entities/rule/api";
import { Button } from "@/shared/ui/Button";
import { Modal } from "@/shared/ui/Modal";
import { Textarea } from "@/shared/ui/Input";

const MAX_CHARS = 500;

export function RuleList({
  rules,
  owner,
  repo,
  maxRules = 10,
  onCreated,
  onUpdated,
  onDeleted,
  onImported,
}) {
  // Add rule modal
  const [addOpen, setAddOpen] = useState(false);
  const [addText, setAddText] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState(null);

  // Edit modal
  const [editRule, setEditRule] = useState(null);
  const [editText, setEditText] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState(null);

  // Delete modal
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Toggle loading per rule
  const [toggling, setToggling] = useState(new Set());

  // Import/Export
  const fileRef = useRef(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  async function handleAdd(e) {
    e.preventDefault();
    const trimmed = addText.trim();
    if (!trimmed) return;
    setAddLoading(true);
    setAddError(null);
    try {
      const rule = await createRule(owner, repo, trimmed);
      setAddText("");
      setAddOpen(false);
      onCreated?.(rule);
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAddLoading(false);
    }
  }

  function openEdit(rule) {
    setEditRule(rule);
    setEditText(rule.rule_text);
    setEditError(null);
  }

  async function handleEdit(e) {
    e.preventDefault();
    const trimmed = editText.trim();
    if (!trimmed || !editRule) return;
    setEditLoading(true);
    setEditError(null);
    try {
      const updated = await updateRule(owner, repo, editRule.id, { rule_text: trimmed });
      setEditRule(null);
      onUpdated?.(updated);
    } catch (err) {
      setEditError(err.message);
    } finally {
      setEditLoading(false);
    }
  }

  async function handleToggle(rule) {
    setToggling((prev) => new Set([...prev, rule.id]));
    try {
      const updated = await updateRule(owner, repo, rule.id, { enabled: !rule.enabled });
      onUpdated?.(updated);
    } catch {}
    finally {
      setToggling((prev) => { const n = new Set(prev); n.delete(rule.id); return n; });
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await deleteRule(owner, repo, deleteTarget.id);
      onDeleted?.(deleteTarget.id);
      setDeleteTarget(null);
    } finally {
      setDeleteLoading(false);
    }
  }

  function handleExport() {
    const payload = { rules: rules.map((r) => r.rule_text) };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rules-${owner}-${repo}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImportResult(null);

    let parsed;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setImportResult({ error: "El fichero no es un JSON válido." });
      return;
    }

    const incoming = parsed?.rules;
    if (!Array.isArray(incoming) || incoming.length === 0) {
      setImportResult({ error: 'El JSON no contiene un array "rules" válido.' });
      return;
    }

    const slots = maxRules - rules.length;
    const toAdd = incoming.slice(0, slots);
    const skipped = incoming.length - toAdd.length;

    if (toAdd.length === 0) {
      setImportResult({ error: `Límite de ${maxRules} reglas alcanzado.` });
      return;
    }

    setImporting(true);
    let added = 0;
    const errors = [];
    const created = [];

    for (const text of toAdd) {
      const trimmed = String(text).trim().slice(0, 500);
      if (!trimmed) continue;
      try {
        const rule = await createRule(owner, repo, trimmed);
        created.push(rule);
        added++;
      } catch (err) {
        errors.push(err.message);
      }
    }

    setImporting(false);
    setImportResult({ added, skipped, errors });
    if (created.length) onImported?.(created);
  }

  const canAdd = rules.length < maxRules;

  return (
    <>
      {/* Header bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--color-text)]">
              {rules.length}/{maxRules} reglas definidas
            </span>
          </div>
          {rules.length > 0 && (
            <div className="mt-1 h-1.5 w-40 rounded-full bg-[var(--color-border)] overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${rules.length >= maxRules ? "bg-amber-500" : "bg-indigo-500"}`}
                style={{ width: `${(rules.length / maxRules) * 100}%` }}
              />
            </div>
          )}
        </div>

        <button
          onClick={() => fileRef.current?.click()}
          disabled={importing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-text-muted)] transition-colors disabled:opacity-50"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          Importar JSON
        </button>
        <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFileChange} />

        {rules.length > 0 && (
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-text-muted)] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
            Exportar JSON
          </button>
        )}

        <button
          onClick={() => { setAddText(""); setAddError(null); setAddOpen(true); }}
          disabled={!canAdd}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Añadir regla
        </button>
      </div>

      {/* Import feedback */}
      {importResult?.error && (
        <p className="text-xs text-red-400 mb-2">{importResult.error}</p>
      )}
      {importResult && !importResult.error && (
        <div className="text-xs space-y-0.5 mb-2">
          <p className="text-emerald-400">
            {importResult.added} regla{importResult.added !== 1 ? "s" : ""} importada{importResult.added !== 1 ? "s" : ""}.
          </p>
          {importResult.skipped > 0 && (
            <p className="text-amber-400">{importResult.skipped} omitida{importResult.skipped !== 1 ? "s" : ""} por límite.</p>
          )}
          {importResult.errors.map((e, i) => (
            <p key={i} className="text-red-400">{e}</p>
          ))}
        </div>
      )}

      {/* Rules list */}
      {rules.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-10 text-center">
          <p className="text-sm text-[var(--color-text-muted)]">
            No hay reglas definidas. Añade la primera con el botón de arriba.
          </p>
        </div>
      ) : (
        <ol className="flex flex-col gap-2">
          {rules.map((rule) => (
            <li
              key={rule.id}
              className={`flex items-center gap-3 rounded-lg border px-4 py-3 group transition-colors ${
                rule.enabled
                  ? "border-[var(--color-border)] bg-[var(--color-surface-2)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface)] opacity-60"
              }`}
            >
              {/* Toggle */}
              <button
                onClick={() => handleToggle(rule)}
                disabled={toggling.has(rule.id)}
                className="flex-shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none disabled:opacity-50"
                style={{ backgroundColor: rule.enabled ? "rgb(99 102 241)" : "rgb(75 85 99)" }}
                title={rule.enabled ? "Deshabilitar regla" : "Habilitar regla"}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    rule.enabled ? "translate-x-4" : "translate-x-1"
                  }`}
                />
              </button>

              {/* Rule text */}
              <p className={`flex-1 text-sm leading-relaxed ${rule.enabled ? "text-[var(--color-text)]" : "text-[var(--color-text-muted)]"}`}>
                {rule.rule_text}
              </p>

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => openEdit(rule)}
                  className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
                  title="Editar regla"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button
                  onClick={() => setDeleteTarget(rule)}
                  className="p-1 text-[var(--color-text-muted)] hover:text-red-400 transition-colors"
                  title="Eliminar regla"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {/* Add rule modal */}
      <Modal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Añadir regla de validación"
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>Cancelar</Button>
            <Button loading={addLoading} disabled={!addText.trim()} onClick={handleAdd}>Añadir</Button>
          </>
        }
      >
        <form onSubmit={handleAdd} className="flex flex-col gap-3">
          <Textarea
            label="Regla"
            placeholder="Ej: Todos los métodos públicos deben tener tests unitarios."
            rows={3}
            value={addText}
            onChange={(e) => setAddText(e.target.value)}
            maxLength={MAX_CHARS}
            error={addError}
            hint={`${MAX_CHARS - addText.length} caracteres restantes`}
          />
        </form>
      </Modal>

      {/* Edit rule modal */}
      <Modal
        open={!!editRule}
        onClose={() => setEditRule(null)}
        title="Editar regla"
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditRule(null)}>Cancelar</Button>
            <Button loading={editLoading} disabled={!editText.trim()} onClick={handleEdit}>Guardar</Button>
          </>
        }
      >
        <form onSubmit={handleEdit} className="flex flex-col gap-3">
          <Textarea
            label="Regla"
            rows={3}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            maxLength={MAX_CHARS}
            error={editError}
            hint={`${MAX_CHARS - editText.length} caracteres restantes`}
          />
        </form>
      </Modal>

      {/* Delete confirm modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar regla"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
            <Button variant="danger" loading={deleteLoading} onClick={handleDelete}>Eliminar</Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-muted)]">
          ¿Estás seguro de que quieres eliminar esta regla? Esta acción no se puede deshacer.
        </p>
        {deleteTarget && (
          <div className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)]">
            {deleteTarget.rule_text}
          </div>
        )}
      </Modal>
    </>
  );
}
