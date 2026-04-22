import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchTask } from "@/entities/task/api";
import { isTerminal, TASK_STATUS } from "@/entities/task/model";
import { useTaskWebSocket } from "@/features/auth/useTaskWebSocket";
import { TaskResultPanel } from "@/widgets/TaskResultPanel/TaskResultPanel";
import { PageLoader } from "@/shared/ui/Spinner";
import { Badge } from "@/shared/ui/Badge";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { formatDate, formatDuration, statusColor } from "@/shared/lib/utils";

const STATUS_LABELS = {
  pending: "Pendiente",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Fallido",
};

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
      <div className="p-6 text-center text-[var(--color-text-muted)]">
        Evaluación no encontrada.
      </div>
    );
  }

  const isRunning =
    task.status === TASK_STATUS.RUNNING || task.status === TASK_STATUS.PENDING;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
        <Link
          to="/tasks"
          className="hover:text-[var(--color-text)] transition-colors"
        >
          Evaluaciones
        </Link>
        <span>/</span>
        <span className="text-[var(--color-text)] font-mono text-xs">
          {taskId.slice(0, 8)}…
        </span>
      </nav>

      {/* Header */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge color={statusColor(task.status)}>
                {isRunning && (
                  <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
                )}
                {STATUS_LABELS[task.status] ?? task.status}
              </Badge>
              {task.pr_number && (
                <Badge color="primary">PR #{task.pr_number}</Badge>
              )}
            </div>
            <Link
              to={`/repos/${task.repository_full_name}`}
              className="inline-flex items-center gap-1.5 group"
            >
              <h1 className="text-xl font-bold text-[var(--color-text)] group-hover:text-indigo-400 transition-colors">
                {task.repository_full_name}
              </h1>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4 text-[var(--color-text-muted)] group-hover:text-indigo-400 transition-colors"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
              </svg>
            </Link>
            <p className="text-xs text-[var(--color-text-muted)] mt-1 font-mono">
              {taskId}
            </p>
          </div>
          <div className="text-right text-xs text-[var(--color-text-muted)] space-y-1">
            <p>
              Creado:{" "}
              <span className="text-[var(--color-text)]">
                {formatDate(task.created_at)}
              </span>
            </p>
            {task.started_at && (
              <p>
                Iniciado:{" "}
                <span className="text-[var(--color-text)]">
                  {formatDate(task.started_at)}
                </span>
              </p>
            )}
            {task.completed_at && (
              <p>
                Duración:{" "}
                <span className="text-[var(--color-text)]">
                  {formatDuration(task.started_at, task.completed_at)}
                </span>
              </p>
            )}
          </div>
        </div>

        {/* Progress */}
        {isRunning && (
          <div className="mt-4 space-y-2">
            <ProgressBar value={task.progress ?? 0} color="primary" />
            <p className="text-xs text-[var(--color-text-muted)]">
              {task.progress_message ?? "Procesando…"} ({task.progress ?? 0}%)
            </p>
          </div>
        )}

        {/* Error */}
        {task.status === TASK_STATUS.FAILED && task.error && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {task.error}
          </div>
        )}
      </div>

      {/* Rules used */}
      {task.rules?.length > 0 && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text)] mb-3">
            Reglas evaluadas ({task.rules.length})
          </h2>
          <ol className="space-y-1.5">
            {task.rules.map((r, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-[var(--color-text-muted)]"
              >
                <span className="text-xs font-bold text-indigo-400 mt-0.5">
                  {i + 1}.
                </span>
                {r.rule_text ?? r}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Results */}
      {task.result && <TaskResultPanel result={task.result} />}

      {/* Loading spinner while running */}
      {isRunning && (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <div className="h-8 w-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Evaluación en progreso… los resultados aparecerán aquí
            automáticamente.
          </p>
        </div>
      )}
    </div>
  );
}
