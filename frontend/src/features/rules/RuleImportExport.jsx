import { useRef, useState } from "react";
import { createRule } from "@/entities/rule/api";
import { Button } from "@/shared/ui/Button";

const MAX_RULES = 10;

export function RuleImportExport({ owner, repo, rules, onImported }) {
  const fileRef = useRef(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null); // { added, skipped, errors }

  // ── Import ────────────────────────────────────────────────────────────────

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    let parsed;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setResult({ error: "El fichero no es un JSON válido." });
      return;
    }

    const incoming = parsed?.rules;
    if (!Array.isArray(incoming) || incoming.length === 0) {
      setResult({ error: 'El JSON no contiene un array "rules" válido.' });
      return;
    }

    const slots = MAX_RULES - rules.length;
    const toAdd = incoming.slice(0, slots);
    const skipped = incoming.length - toAdd.length;

    if (toAdd.length === 0) {
      setResult({
        error: `Límite de ${MAX_RULES} reglas alcanzado. Elimina alguna antes de importar.`,
      });
      return;
    }

    setImporting(true);
    setResult(null);

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
    setResult({ added, skipped, errors });
    if (created.length) onImported?.(created);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {/* Import */}
        <Button
          variant="secondary"
          size="sm"
          loading={importing}
          onClick={() => fileRef.current?.click()}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
              clipRule="evenodd"
            />
          </svg>
          Importar JSON
        </Button>

        <input
          ref={fileRef}
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* Feedback */}
      {result?.error && <p className="text-xs text-[var(--taro-incorrect-ink)]">{result.error}</p>}
      {result && !result.error && (
        <div className="text-xs space-y-0.5">
          <p className="text-[var(--taro-correct-ink)]">
            {result.added} regla{result.added !== 1 ? "s" : ""} importada
            {result.added !== 1 ? "s" : ""}.
          </p>
          {result.skipped > 0 && (
            <p className="text-[var(--taro-partial-ink)]">
              {result.skipped} omitida{result.skipped !== 1 ? "s" : ""} por
              límite de {MAX_RULES}.
            </p>
          )}
          {result.errors.map((e, i) => (
            <p key={i} className="text-[var(--taro-incorrect-ink)]">
              {e}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
