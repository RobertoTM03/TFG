import { useState } from "react";
import { Card, CardGrid, CardCell } from "@/shared/ui/Card";
import { Eyebrow, Body, Mono } from "@/shared/ui/Typography";
import { statusStyle, statusLabel } from "@/shared/lib/status";
import { formatScore } from "@/shared/lib/utils";
import { computeOverallScore, verdictCounts } from "@/entities/task/model";

function VerdictLabel({ verdict }) {
  const { ink } = statusStyle("verdict", verdict);
  return (
    <Mono
      style={{ color: `var(${ink})` }}
      className="text-[10.5px] font-semibold uppercase tracking-[0.16em]"
    >
      {statusLabel("verdict", verdict)}
    </Mono>
  );
}

function CrossCheckRow({ label, model, verdict, children }) {
  return (
    <div className="flex flex-col gap-2 border-t border-[var(--taro-line)] pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="flex flex-wrap items-center gap-2">
          <Eyebrow>{label}</Eyebrow>
          {model && (
            <Mono className="text-[11.5px] text-[var(--taro-ink-muted)]">
              {model}
            </Mono>
          )}
        </span>
        {verdict && <VerdictLabel verdict={verdict} />}
      </div>
      {children && (
        <Body muted className="min-h-[22px] text-[13.5px]">
          {children}
        </Body>
      )}
    </div>
  );
}

function CrossCheck({ cc }) {
  const tone = cc.agreement ? "correct" : "partial";
  const { ink, ground } = statusStyle("tone", tone);

  return (
    <div className="rounded-[var(--taro-radius-row)] bg-[var(--taro-raised)] p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Eyebrow>Verificación cruzada</Eyebrow>
        <span
          style={{ color: `var(${ink})`, background: `var(${ground})` }}
          className="inline-flex items-center whitespace-nowrap rounded-[var(--taro-radius-control)] px-[10px] py-[4px] font-[family-name:var(--taro-font-mono)] text-[11px] font-medium leading-none"
        >
          {cc.agreement
            ? "Los modelos coinciden"
            : "Sin acuerdo · discriminador usado"}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        <CrossCheckRow
          label="primario"
          model={cc.primary_model}
          verdict={cc.primary_verdict}
        >
          {cc.primary_explanation}
        </CrossCheckRow>

        <CrossCheckRow
          label="secundario"
          model={cc.secondary_model}
          verdict={cc.secondary_verdict}
        >
          {cc.secondary_explanation}
        </CrossCheckRow>

        {cc.discriminator_used && (
          <CrossCheckRow label="discriminador" model={cc.discriminator_model}>
            {cc.discriminator_reasoning}
          </CrossCheckRow>
        )}
      </div>
    </div>
  );
}

function ValidationCard({ v }) {
  const [expanded, setExpanded] = useState(false);
  const verdict = v.evaluation?.verdict;
  const explanation = v.evaluation?.explanation;
  const suggestions = v.evaluation?.suggestions ?? [];
  const files = v.related_files ?? [];
  const cc = v.cross_check;

  const { accent } = statusStyle("verdict", verdict);

  return (
    <Card accent={accent} flush className="overflow-hidden">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex w-full cursor-pointer items-start justify-between gap-6 px-[26px] py-[22px] text-left transition-[background-color] duration-[250ms] hover:bg-[var(--taro-raised)]"
      >
        <Body className="flex-1">{v.rule}</Body>
        <span className="shrink-0 pt-1">
          <VerdictLabel verdict={verdict} />
        </span>
      </button>

      {expanded && (
        <div className="flex flex-col gap-6 border-t border-[var(--taro-line)] px-[26px] py-[22px]">
          {explanation && <Body muted>{explanation}</Body>}

          {suggestions.length > 0 && (
            <div className="flex flex-col gap-2">
              <Eyebrow>Sugerencias</Eyebrow>
              <ul className="flex flex-col gap-2">
                {suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-[9px] h-[3px] w-[3px] shrink-0 rounded-full bg-[var(--taro-brass)]" />
                    <Body muted className="flex-1">
                      {s}
                    </Body>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {files.length > 0 && (
            <div className="flex flex-col gap-2">
              <Eyebrow>Archivos citados</Eyebrow>
              <div className="flex flex-wrap gap-2">
                {files.map((f, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-2 rounded-[var(--taro-radius-control)] bg-[var(--taro-inset)] px-[10px] py-[6px]"
                  >
                    <Mono className="text-[11.5px] text-[var(--taro-ink-muted)]">
                      {f.file_path}
                      {f.truncated && "…"}
                    </Mono>
                    <Mono className="text-[11.5px] text-[var(--taro-ink-dim)]">
                      {formatScore(f.relevance_score)}
                    </Mono>
                  </span>
                ))}
              </div>
            </div>
          )}

          {cc && <CrossCheck cc={cc} />}
        </div>
      )}
    </Card>
  );
}

export function TaskResultPanel({ result }) {
  if (!result) return null;

  const { validations = [] } = result;
  const score = computeOverallScore(validations);
  const counts = verdictCounts(validations);

  const cells = [
    ["Puntuación global", formatScore(score), null],
    ["Correctas", counts.pass, "correct"],
    ["Parciales", counts.partial, "partial"],
    ["Incorrectas", counts.fail, "incorrect"],
  ];

  return (
    <div className="flex flex-col gap-6">
      <CardGrid columns={2}>
        {cells.map(([label, value, tone]) => (
          <CardCell key={label}>
            <Mono
              style={tone ? { color: `var(${statusStyle("tone", tone).ink})` } : undefined}
              className="block text-[30px] leading-none text-[var(--taro-ink)]"
            >
              {value}
            </Mono>
            <Eyebrow className="mt-3 block">{label}</Eyebrow>
          </CardCell>
        ))}
      </CardGrid>

      <div className="flex flex-col gap-3">
        <Eyebrow>Validaciones, regla a regla</Eyebrow>
        {validations.map((v, i) => (
          <ValidationCard key={i} v={v} />
        ))}
      </div>
    </div>
  );
}
