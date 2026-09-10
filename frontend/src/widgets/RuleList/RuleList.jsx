import { useRef, useState } from "react";
import { createRule, updateRule, deleteRule } from "@/entities/rule/api";
import { Button } from "@/shared/ui/Button";
import { Modal } from "@/shared/ui/Modal";
import { Textarea } from "@/shared/ui/Input";
import { Card } from "@/shared/ui/Card";
import { Eyebrow, Body, Mono } from "@/shared/ui/Typography";

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

  // Delete all modal
  const [deleteAllOpen, setDeleteAllOpen] = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);

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

  async function handleDeleteAll() {
    setDeleteAllLoading(true);
    try {
      await Promise.all(rules.map((r) => deleteRule(owner, repo, r.id)));
      rules.forEach((r) => onDeleted?.(r.id));
      setDeleteAllOpen(false);
    } finally {
      setDeleteAllLoading(false);
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
      {/* Barra de cabecera */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[180px]">
          <Eyebrow className="block">
            {rules.length} / {maxRules} reglas
          </Eyebrow>
          {rules.length > 0 && (
            <div className="mt-2 h-[4px] w-40 overflow-hidden rounded-[var(--taro-radius-control)] bg-[var(--taro-line)]">
              <div
                className="h-full rounded-[var(--taro-radius-control)] bg-[var(--taro-brass)]"
                style={{ width: `${(rules.length / maxRules) * 100}%` }}
              />
            </div>
          )}
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => fileRef.current?.click()}
          disabled={importing}
        >
          Importar JSON
        </Button>
        <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFileChange} />

        {rules.length > 0 && (
          <>
            <Button variant="secondary" size="sm" onClick={handleExport}>
              Exportar JSON
            </Button>
            <Button variant="danger" size="sm" onClick={() => setDeleteAllOpen(true)}>
              Eliminar todas
            </Button>
          </>
        )}

        <Button
          size="sm"
          onClick={() => { setAddText(""); setAddError(null); setAddOpen(true); }}
          disabled={!canAdd}
        >
          Añadir regla
        </Button>
      </div>

      {importResult && (
        <div className="mb-4 min-h-[20px] text-[12px] leading-[20px]">
          {importResult.error ? (
            <p className="text-[var(--taro-incorrect-ink)]">{importResult.error}</p>
          ) : (
            <>
              <p className="text-[var(--taro-correct-ink)]">
                {importResult.added} regla{importResult.added !== 1 ? "s" : ""} importada{importResult.added !== 1 ? "s" : ""}.
              </p>
              {importResult.skipped > 0 && (
                <p className="text-[var(--taro-partial-ink)]">
                  {importResult.skipped} omitida{importResult.skipped !== 1 ? "s" : ""} por límite.
                </p>
              )}
              {importResult.errors.map((e, i) => (
                <p key={i} className="text-[var(--taro-incorrect-ink)]">{e}</p>
              ))}
            </>
          )}
        </div>
      )}

      {/* Lista de reglas */}
      {rules.length === 0 ? (
        <Card className="text-center">
          <Body muted>
            No hay reglas definidas. Añade la primera con el botón de arriba.
          </Body>
        </Card>
      ) : (
        <ol className="flex flex-col gap-px overflow-hidden rounded-[var(--taro-radius-card)] border border-[var(--taro-line)] bg-[var(--taro-line)]">
          {rules.map((rule, i) => (
            <li
              key={rule.id}
              className="group flex items-center gap-4 bg-[var(--taro-surface)] px-5 py-4 transition-[background-color] duration-[250ms] hover:bg-[var(--taro-raised)]"
            >
              <Mono className="w-6 shrink-0 text-[11.5px] text-[var(--taro-ink-dim)]">
                {String(i + 1).padStart(2, "0")}
              </Mono>

              <Body
                className={`flex-1 ${rule.enabled ? "" : "text-[var(--taro-ink-dim)]"}`}
              >
                {rule.rule_text}
              </Body>

              <Mono
                className={`shrink-0 text-[10.5px] font-medium uppercase tracking-[0.16em] ${
                  rule.enabled ? "text-[var(--taro-ink-muted)]" : "text-[var(--taro-ink-dim)]"
                }`}
              >
                {rule.enabled ? "activa" : "off"}
              </Mono>

              <button
                onClick={() => handleToggle(rule)}
                disabled={toggling.has(rule.id)}
                title={rule.enabled ? "Deshabilitar regla" : "Habilitar regla"}
                className={`relative inline-flex h-[20px] w-[36px] shrink-0 cursor-pointer items-center rounded-full transition-[background-color] duration-[250ms] disabled:cursor-not-allowed disabled:opacity-50 ${
                  rule.enabled ? "bg-[var(--taro-brass)]" : "bg-[var(--taro-line-strong)]"
                }`}
              >
                <span
                  className={`inline-block h-[14px] w-[14px] rounded-full transition-transform duration-[250ms] ${
                    rule.enabled
                      ? "translate-x-[19px] bg-[var(--taro-brass-ink)]"
                      : "translate-x-[3px] bg-[var(--taro-ink-dim)]"
                  }`}
                />
              </button>

              <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity duration-[250ms] group-hover:opacity-100">
                <button
                  onClick={() => openEdit(rule)}
                  title="Editar regla"
                  className="cursor-pointer p-1 text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-ink)]"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button
                  onClick={() => setDeleteTarget(rule)}
                  title="Eliminar regla"
                  className="cursor-pointer p-1 text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-incorrect-ink)]"
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

      {/* Delete all confirm modal */}
      <Modal
        open={deleteAllOpen}
        onClose={() => setDeleteAllOpen(false)}
        title="Eliminar todas las reglas"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteAllOpen(false)}>Cancelar</Button>
            <Button variant="danger" loading={deleteAllLoading} onClick={handleDeleteAll}>Eliminar todas</Button>
          </>
        }
      >
        <p className="text-[14px] leading-[1.6] text-[var(--taro-ink-muted)]">
          ¿Estás seguro? Se eliminarán <strong className="text-[var(--taro-ink)]">{rules.length} regla{rules.length !== 1 ? "s" : ""}</strong>. Esta acción no se puede deshacer.
        </p>
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
        <p className="text-[14px] leading-[1.6] text-[var(--taro-ink-muted)]">
          ¿Estás seguro de que quieres eliminar esta regla? Esta acción no se puede deshacer.
        </p>
        {deleteTarget && (
          <div className="mt-3 rounded-[var(--taro-radius-row)] border border-[var(--taro-line-strong)] bg-[var(--taro-raised)] px-3 py-2 text-[14px] leading-[1.6] text-[var(--taro-ink)]">
            {deleteTarget.rule_text}
          </div>
        )}
      </Modal>
    </>
  );
}
