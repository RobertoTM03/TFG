import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchTask } from "@/entities/task/api";
import { isTerminal, TASK_STATUS, parseTaskError } from "@/entities/task/model";
import { useTaskWebSocket } from "@/features/auth/useTaskWebSocket";
import { TaskResultPanel } from "@/widgets/TaskResultPanel/TaskResultPanel";
import { PageLoader, Spinner } from "@/shared/ui/Spinner";
import { Badge } from "@/shared/ui/Badge";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { Card } from "@/shared/ui/Card";
import { Eyebrow, Body, Mono, SectionTitle, PageTitle } from "@/shared/ui/Typography";
import { formatDate, formatDuration, formatScore } from "@/shared/lib/utils";
import { statusStyle } from "@/shared/lib/status";
import { computeOverallScore } from "@/entities/task/model";

const GH = "https://github.com";

export function TaskDetailPage() {
  const { taskId } = useParams();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    fetchTask(taskId)
      .then(setTask)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [taskId]);

  useEffect(() => {
    load();
  }, [load]);

  // Polling fallback: re-fetch every 3s while not terminal.
  // Covers the race condition where the task finishes before the WS subscription completes.
  useEffect(() => {
    if (!task?.status || isTerminal(task.status)) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [task?.status, load]);

  // WebSocket: instant updates when the backend pushes progress events.
  useTaskWebSocket(
    !isTerminal(task?.status) ? taskId : null,
    useCallback(
      (msg) => {
        setTask((prev) => {
          if (!prev) return prev;
          const updated = {
            ...prev,
            status: msg.status,
            progress: msg.progress ?? prev.progress,
            progress_message: msg.message ?? prev.progress_message,
          };
          if (isTerminal(msg.status)) {
            fetchTask(taskId)
              .then(setTask)
              .catch(() => {});
          }
          return updated;
        });
      },
      [taskId],
    ),
  );

  if (loading) return <PageLoader />;
  if (!task) {
    return (
      <div className="px-8 py-10 text-center text-[var(--taro-ink-muted)]">
        Evaluación no encontrada.
      </div>
    );
  }

  const isRunning =
    task.status === TASK_STATUS.RUNNING || task.status === TASK_STATUS.PENDING;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-8 py-10">
      {/* Migas */}
      <nav className="flex items-center gap-2 text-[13px] text-[var(--taro-ink-dim)]">
        <Link to="/tasks" className="text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-ink)] hover:no-underline">
          Evaluaciones
        </Link>
        <span>/</span>
        <Mono className="text-[12px] text-[var(--taro-ink-muted)]">
          {taskId.slice(0, 8)}
        </Mono>
      </nav>

      {/* Cabecera */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge kind="task" value={task.status} />
              {task.pr_number && (
                <a
                  href={`${GH}/${task.repository_full_name}/pull/${task.pr_number}`}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:no-underline"
                >
                  <Badge kind="tone" value="brass">PR #{task.pr_number}</Badge>
                </a>
              )}
              {task.pr_head_ref && (
                <a
                  href={`${GH}/${task.repository_full_name}/tree/${task.pr_head_ref}`}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:no-underline"
                >
                  <Badge kind="tone" value="neutral">{task.pr_head_ref}</Badge>
                </a>
              )}
            </div>

            <Link to={`/repos/${task.repository_full_name}`} className="hover:no-underline">
              <PageTitle className="truncate transition-[color] duration-[250ms] hover:text-[var(--taro-brass)]">
                {task.repository_full_name}
              </PageTitle>
            </Link>

            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2">
              {[
                ["llm_model", task.llm_model],
                ["embedding_model", task.embedding_model],
                ["chunking_strategy", task.chunking_strategy],
              ]
                .filter(([, v]) => v)
                .map(([label, value]) => (
                  <span key={label} className="flex items-center gap-2">
                    <Mono className="text-[11.5px] text-[var(--taro-ink-dim)]">{label}</Mono>
                    <Mono className="text-[11.5px] text-[var(--taro-ink-muted)]">{value}</Mono>
                  </span>
                ))}
            </div>
          </div>

          <div className="shrink-0 text-right">
            {(() => {
              const score = computeOverallScore(task.result?.validations ?? []);
              if (score == null) return null;
              const ink = statusStyle("task", task.status).ink;
              return (
                <>
                  <Mono
                    style={{ color: `var(${ink})` }}
                    className="block text-[40px] leading-none tracking-[-1.5px]"
                  >
                    {formatScore(score)}
                  </Mono>
                  <Eyebrow className="mt-2 block normal-case tracking-[0.08em]">
                    puntuación global · umbral {formatScore(task.approval_threshold)}
                  </Eyebrow>
                </>
              );
            })()}
            <div className="mt-4 flex flex-col items-end gap-1">
              <Eyebrow className="normal-case tracking-[0.06em]">
                creado {formatDate(task.created_at)}
              </Eyebrow>
              {task.completed_at && (
                <Eyebrow className="normal-case tracking-[0.06em]">
                  duración {formatDuration(task.started_at, task.completed_at)}
                </Eyebrow>
              )}
            </div>
          </div>
        </div>

        {/* Retry warning */}
        {isRunning && task.retry_count > 4 && (
          <div className="mt-6 rounded-[var(--taro-radius-row)] border border-[var(--taro-partial-line)] bg-[var(--taro-partial-bg)] px-4 py-3 text-[13.5px] leading-[1.6] text-[var(--taro-partial-ink)]">
            La evaluación está tardando más de lo esperado debido a problemas temporales con el servicio.
            Se reanudará automáticamente — no es necesario hacer nada.
            {task.retry_count > 1 && (
              <span className="ml-1">(intento {task.retry_count})</span>
            )}
          </div>
        )}

        {/* Progress */}
        {isRunning && (
          <div className="mt-6 flex flex-col gap-2">
            <ProgressBar value={task.progress ?? 0} />
            <Eyebrow className="normal-case tracking-[0.06em]">
              {task.progress_message || "Procesando…"}{task.retry_count <= 4 && ` (${task.progress ?? 0}%)`}
            </Eyebrow>
          </div>
        )}

        {/* Error */}
        {task.status === TASK_STATUS.FAILED && task.error && (() => {
          const err = parseTaskError(task.error);
          return (
            <div
              style={{ borderColor: `var(${statusStyle("error", err.code).line})` }}
              className="mt-6 rounded-[var(--taro-radius-row)] border bg-[var(--taro-incorrect-bg)] px-4 py-3"
            >
              <p className="text-[13.5px] font-semibold text-[var(--taro-incorrect-ink)]">{err.title}</p>
              <p className="mt-1 min-h-[22px] text-[13.5px] leading-[22px] text-[var(--taro-incorrect-ink)] [text-wrap:pretty]">
                {err.message}
              </p>
              {err.technical && (
                <details className="mt-2">
                  <summary className="cursor-pointer font-[family-name:var(--taro-font-mono)] text-[11px] uppercase tracking-[0.14em] text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-ink-muted)]">
                    Detalles técnicos
                  </summary>
                  <pre className="mt-2 overflow-x-auto rounded-[var(--taro-radius-control)] bg-[var(--taro-inset)] p-3 font-[family-name:var(--taro-font-mono)] text-[11.5px] whitespace-pre-wrap break-all text-[var(--taro-ink-dim)]">
                    {err.technical}
                  </pre>
                </details>
              )}
            </div>
          );
        })()}
      </Card>

      {/* Reglas evaluadas */}
      {task.rules?.length > 0 && (
        <Card>
          <SectionTitle className="mb-5">
            Reglas evaluadas ({task.rules.length})
          </SectionTitle>
          <ol className="flex flex-col gap-3">
            {task.rules.map((r, i) => (
              <li key={i} className="flex items-start gap-4">
                <Mono className="mt-[3px] w-6 shrink-0 text-[11.5px] text-[var(--taro-ink-dim)]">
                  {String(i + 1).padStart(2, "0")}
                </Mono>
                <Body muted className="flex-1">{r.rule_text ?? r}</Body>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {/* Results */}
      {task.result && <TaskResultPanel result={task.result} />}

      {/* Loading spinner while running */}
      {isRunning && (
        <div className="flex flex-col items-center gap-4 py-10 text-center">
          <Spinner />
          <Body muted>
            Evaluación en progreso… los resultados aparecerán aquí automáticamente.
          </Body>
        </div>
      )}
    </div>
  );
}
