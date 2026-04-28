import { useRef, useState } from "react";
import { createRule, deleteRule } from "@/entities/rule/api";
import { Button } from "@/shared/ui/Button";
import { Modal } from "@/shared/ui/Modal";

export function RuleList({
  rules,
  owner,
  repo,
  maxRules = 10,
  onDeleted,
  onDeletedMany,
  onImported,
}) {
  const [selected, setSelected] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  const [confirmMode, setConfirmMode] = useState(null); // null | 'single' | 'bulk'
  const [confirmSingleId, setConfirmSingleId] = useState(null);

  // Import state
  const fileRef = useRef(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const allSelected = rules.length > 0 && selected.size === rules.length;
  const someSelected = selected.size > 0 && !allSelected;

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(rules.map((r) => r.id)));
  }

  function toggleOne(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleDeleteSingle(ruleId) {
    setDeleting(true);
    try {
      await deleteRule(owner, repo, ruleId);
      setSelected((prev) => { const n = new Set(prev); n.delete(ruleId); return n; });
      onDeleted?.(ruleId);
    } finally {
      setDeleting(false);
      setConfirmMode(null);
      setConfirmSingleId(null);
    }
  }

  async function handleDeleteBulk() {
    const ids = [...selected];
    setDeleting(true);
    const deleted = [];
    for (const id of ids) {
      try {
        await deleteRule(owner, repo, id);
        deleted.push(id);
      } catch {}
    }
    setDeleting(false);
    setConfirmMode(null);
    setSelected(new Set());
    if (deleted.length) onDeletedMany?.(deleted);
  }

  function handleExportSelected() {
    const toExport = rules.filter((r) => selected.has(r.id));
    const payload = { rules: toExport.map((r) => r.rule_text) };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rules-${owner}-${repo}-selected.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

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
      setImportResult({ error: `Límite de ${maxRules} reglas alcanzado. Elimina alguna antes de importar.` });
      return;
    }

    setImporting(true);
    setImportResult(null);

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

  if (!rules?.length) return null;

  const selectedRules = rules.filter((r) => selected.has(r.id));
  const confirmSingleRule = rules.find((r) => r.id === confirmSingleId);

  return (
    <>
      {/* ── Cabecera unificada ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5">
        {/* Checkbox seleccionar todo */}
        <input
          type="checkbox"
          checked={allSelected}
          ref={(el) => { if (el) el.indeterminate = someSelected; }}
          onChange={toggleAll}
          className="h-5 w-5 flex-shrink-0 rounded border-[var(--color-border)] accent-indigo-500 cursor-pointer"
          title={allSelected ? "Deseleccionar todo" : "Seleccionar todo"}
        />

        {/* Contador de selección (ocupa el espacio libre) */}
        <span className="flex-1 text-xs text-[var(--color-text-muted)]">
          {selected.size > 0 ? (
            <>
              <span className="font-medium text-[var(--color-text)]">{selected.size}</span>{" "}
              regla{selected.size !== 1 ? "s" : ""} seleccionada{selected.size !== 1 ? "s" : ""}
            </>
          ) : (
            "Seleccionar todo"
          )}
        </span>

        {/* Acciones de selección — solo visibles cuando hay selección */}
        {selected.size > 0 && (
          <>
            <Button variant="danger" size="sm" onClick={() => setConfirmMode("bulk")}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Eliminar
            </Button>
            <Button variant="secondary" size="sm" onClick={handleExportSelected}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
              Exportar
            </Button>
          </>
        )}

        {/* Importar — siempre visible */}
        <Button variant="secondary" size="sm" loading={importing} onClick={() => fileRef.current?.click()}>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          Importar JSON
        </Button>
        <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFileChange} />
      </div>

      {/* Feedback de importación */}
      {importResult?.error && (
        <p className="text-xs text-red-400 px-1">{importResult.error}</p>
      )}
      {importResult && !importResult.error && (
        <div className="text-xs space-y-0.5 px-1">
          <p className="text-emerald-400">
            {importResult.added} regla{importResult.added !== 1 ? "s" : ""} importada{importResult.added !== 1 ? "s" : ""}.
          </p>
          {importResult.skipped > 0 && (
            <p className="text-amber-400">
              {importResult.skipped} omitida{importResult.skipped !== 1 ? "s" : ""} por límite de {maxRules}.
            </p>
          )}
          {importResult.errors.map((e, i) => (
            <p key={i} className="text-red-400">{e}</p>
          ))}
        </div>
      )}

      {/* ── Lista de reglas ────────────────────────────────────────────────── */}
      <ol className="flex flex-col gap-2">
        {rules.map((rule, idx) => (
          <li
            key={rule.id}
            onClick={() => toggleOne(rule.id)}
            className={`flex items-center gap-3 rounded-lg border px-4 py-3 group transition-colors cursor-pointer ${
              selected.has(rule.id)
                ? "border-indigo-500/40 bg-indigo-500/5"
                : "border-[var(--color-border)] bg-[var(--color-surface-2)]"
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(rule.id)}
              onChange={() => toggleOne(rule.id)}
              onClick={(e) => e.stopPropagation()}
              className="h-5 w-5 flex-shrink-0 rounded border-[var(--color-border)] accent-indigo-500 cursor-pointer"
            />
            <span className="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded bg-indigo-600/20 text-xs font-bold text-indigo-400">
              {idx + 1}
            </span>
            <p className="flex-1 text-sm text-[var(--color-text)] leading-relaxed">
              {rule.rule_text}
            </p>
            <button
              onClick={(e) => { e.stopPropagation(); setConfirmSingleId(rule.id); setConfirmMode("single"); }}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-muted)] hover:text-red-400"
              title="Eliminar regla"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </button>
          </li>
        ))}
      </ol>

      {/* Modal: eliminar una */}
      <Modal
        open={confirmMode === "single"}
        onClose={() => { setConfirmMode(null); setConfirmSingleId(null); }}
        title="Eliminar regla"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setConfirmMode(null); setConfirmSingleId(null); }}>Cancelar</Button>
            <Button variant="danger" loading={deleting} onClick={() => handleDeleteSingle(confirmSingleId)}>Eliminar</Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-muted)]">
          ¿Estás seguro de que quieres eliminar esta regla? Esta acción no se puede deshacer.
        </p>
        {confirmSingleRule && (
          <div className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)]">
            {confirmSingleRule.rule_text}
          </div>
        )}
      </Modal>

      {/* Modal: eliminar seleccionadas */}
      <Modal
        open={confirmMode === "bulk"}
        onClose={() => setConfirmMode(null)}
        title={`Eliminar ${selected.size} regla${selected.size !== 1 ? "s" : ""}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmMode(null)}>Cancelar</Button>
            <Button variant="danger" loading={deleting} onClick={handleDeleteBulk}>
              Eliminar {selected.size} regla{selected.size !== 1 ? "s" : ""}
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text-muted)] mb-3">
          ¿Estás seguro de que quieres eliminar las siguientes reglas? Esta acción no se puede deshacer.
        </p>
        <ul className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
          {selectedRules.map((rule) => (
            <li key={rule.id} className="flex items-start gap-2 rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)]">
              <span className="flex-shrink-0 h-4 w-4 flex items-center justify-center rounded bg-indigo-600/20 text-xs font-bold text-indigo-400 mt-0.5">
                {rules.indexOf(rule) + 1}
              </span>
              <span className="leading-relaxed">{rule.rule_text}</span>
            </li>
          ))}
        </ul>
      </Modal>
    </>
  );
}
