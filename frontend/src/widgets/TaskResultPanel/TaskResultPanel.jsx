import { useState } from "react";
import { Badge } from "@/shared/ui/Badge";
import { verdictColor } from "@/shared/lib/utils";
import { computeOverallScore, verdictCounts } from "@/entities/task/model";

const VERDICT_LABELS = {
  pass: "Correcto",
  fail: "Incorrecto",
  partial: "Parcial",
};
const VERDICT_ICONS = {
  pass: "✓",
  fail: "✗",
  partial: "~",
};

function ScoreCircle({ score }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? "text-emerald-400"
      : pct >= 60
        ? "text-amber-400"
        : "text-red-400";
  return (
    <div className={`text-4xl font-bold tabular-nums ${color}`}>
      {pct}
      <span className="text-xl">%</span>
    </div>
  );
}

function ValidationCard({ v, index }) {
  const [expanded, setExpanded] = useState(false);
  const verdict = v.cross_check?.primary_verdict ?? v.evaluation?.verdict;
  const confidence =
    v.cross_check?.primary_confidence ?? v.evaluation?.confidence;
  const explanation =
    v.cross_check?.primary_explanation ?? v.evaluation?.explanation;
  const suggestions = v.evaluation?.suggestions ?? [];
  const hasCrossCheck = !!v.cross_check;

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <button
        className="w-full flex items-start gap-4 px-5 py-4 text-left hover:bg-[var(--color-surface-2)] transition-colors"
        onClick={() => setExpanded((p) => !p)}
      >
        <div
          className={`flex-shrink-0 mt-0.5 h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${
            verdict === "pass"
              ? "bg-emerald-500/20 text-emerald-400"
              : verdict === "fail"
                ? "bg-red-500/20 text-red-400"
                : "bg-orange-500/20 text-orange-400"
          }`}
        >
          {VERDICT_ICONS[verdict]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-[var(--color-text-muted)]">
              Regla {index + 1}
            </span>
            <Badge color={verdictColor(verdict)}>
              {VERDICT_LABELS[verdict] ?? verdict}
            </Badge>
            {confidence != null && (
              <span className="text-xs text-[var(--color-text-muted)]">
                {Math.round(confidence * 100)}% confianza
              </span>
            )}
            {hasCrossCheck && <Badge color="primary">cross-check</Badge>}
          </div>
          <p className="mt-1 text-sm font-medium text-[var(--color-text)] line-clamp-2">
            {v.rule}
          </p>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`h-4 w-4 flex-shrink-0 text-[var(--color-text-muted)] transition-transform mt-1 ${
            expanded ? "rotate-180" : ""
          }`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-[var(--color-border)] px-5 py-4 space-y-4">
          {/* Rule text */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
              Regla
            </p>
            <p className="text-sm text-[var(--color-text)]">{v.rule}</p>
          </div>

          {/* Explanation */}
          {explanation && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
                Explicación
              </p>
              <p className="text-sm text-[var(--color-text)] leading-relaxed">
                {explanation}
              </p>
            </div>
          )}

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
                Sugerencias
              </p>
              <ul className="space-y-1">
                {suggestions.map((s, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-[var(--color-text)]"
                  >
                    <span className="text-indigo-400 mt-0.5">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Cross-check detail */}
          {hasCrossCheck && (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
                Verificación cruzada
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">
                    Modelo primario
                  </p>
                  <Badge color={verdictColor(v.cross_check.primary_verdict)}>
                    {VERDICT_LABELS[v.cross_check.primary_verdict] ??
                      v.cross_check.primary_verdict}
                  </Badge>
                  <p className="mt-1.5 text-xs text-[var(--color-text-muted)] line-clamp-3">
                    {v.cross_check.primary_explanation}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">
                    Modelo secundario
                  </p>
                  <Badge color={verdictColor(v.cross_check.secondary_verdict)}>
                    {VERDICT_LABELS[v.cross_check.secondary_verdict] ??
                      v.cross_check.secondary_verdict}
                  </Badge>
                  <p className="mt-1.5 text-xs text-[var(--color-text-muted)] line-clamp-3">
                    {v.cross_check.secondary_explanation}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                <span>
                  Estrategia:{" "}
                  <strong className="text-[var(--color-text)]">
                    {v.cross_check.strategy_used}
                  </strong>
                </span>
                <span>·</span>
                <span>
                  Acuerdo:{" "}
                  <strong
                    className={
                      v.cross_check.agreement
                        ? "text-emerald-400"
                        : "text-amber-400"
                    }
                  >
                    {v.cross_check.agreement ? "Sí" : "No"}
                  </strong>
                </span>
              </div>
            </div>
          )}

          {/* Related files */}
          {v.related_files?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
                Archivos relacionados
              </p>
              <div className="flex flex-col gap-1.5">
                {v.related_files.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs rounded bg-[var(--color-surface-2)] px-3 py-1.5"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3.5 w-3.5 text-indigo-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="font-mono text-[var(--color-text)]">
                      {f.file_path}
                    </span>
                    <span className="ml-auto text-[var(--color-text-muted)]">
                      {Math.round(f.relevance_score * 100)}%
                    </span>
                    {f.truncated && <Badge color="warning">truncado</Badge>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TaskResultPanel({ result }) {
  if (!result) return null;

  const { validations = [] } = result;
  const score = computeOverallScore(validations);
  const counts = verdictCounts(validations);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-center">
          <ScoreCircle score={score} />
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            Puntuación global
          </p>
        </div>
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-center">
          <p className="text-3xl font-bold text-emerald-400">{counts.pass}</p>
          <p className="mt-1 text-xs text-emerald-400/70">Correctas</p>
        </div>
        <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4 text-center">
          <p className="text-3xl font-bold text-orange-400">{counts.partial}</p>
          <p className="mt-1 text-xs text-orange-400/70">Parciales</p>
        </div>
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-center">
          <p className="text-3xl font-bold text-red-400">{counts.fail}</p>
          <p className="mt-1 text-xs text-red-400/70">Fallidas</p>
        </div>
      </div>

      {/* Meta */}
      <div className="flex flex-wrap gap-3 text-xs text-[var(--color-text-muted)]">
        {result.llm_model && (
          <span>
            Modelo:{" "}
            <strong className="text-[var(--color-text)]">
              {result.llm_model}
            </strong>
          </span>
        )}
        {result.embedding_model && (
          <span>
            · Embeddings:{" "}
            <strong className="text-[var(--color-text)]">
              {result.embedding_model}
            </strong>
          </span>
        )}
        {result.chunking_strategy && (
          <span>
            · Chunking:{" "}
            <strong className="text-[var(--color-text)]">
              {result.chunking_strategy}
            </strong>
          </span>
        )}
      </div>

      {/* Per-rule cards */}
      <div className="space-y-3">
        {validations.map((v, i) => (
          <ValidationCard key={i} v={v} index={i} />
        ))}
      </div>
    </div>
  );
}
