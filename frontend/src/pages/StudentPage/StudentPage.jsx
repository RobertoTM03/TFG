import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchStudentTasks,
  fetchStudentSummary,
} from "../../entities/student/api";
import { TaskTable } from "../../widgets/TaskTable/TaskTable";
import { PageLoader } from "../../shared/ui/Spinner";
import { Button } from "../../shared/ui/Button";
import { EmptyState } from "../../shared/ui/EmptyState";
import { formatDate } from "../../shared/lib/utils";

function scoreColor(score) {
  if (score === null || score === undefined) return null;
  if (score >= 8) return "success";
  if (score >= 5) return "warning";
  return "danger";
}

function ScoreDisplay({ score, size = "lg" }) {
  if (score === null || score === undefined) {
    return <span className="text-[var(--color-text-muted)]">—</span>;
  }
  const colorMap = {
    success: "text-[var(--color-success)]",
    warning: "text-amber-400",
    danger: "text-[var(--color-danger)]",
  };
  const cls = colorMap[scoreColor(score)] ?? "text-[var(--color-text)]";
  return (
    <span
      className={`${cls} tabular-nums font-bold ${size === "lg" ? "text-3xl" : "text-xl"}`}
    >
      {score.toFixed(1)}
      <span className="text-sm font-normal text-[var(--color-text-muted)]">
        /10
      </span>
    </span>
  );
}

function VerdictBar({ passCount, partialCount, failCount }) {
  const total = passCount + partialCount + failCount;
  if (total === 0) return null;
  const pPct = (passCount / total) * 100;
  const tPct = (partialCount / total) * 100;
  const fPct = (failCount / total) * 100;
  return (
    <div className="mt-2">
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-2)]">
        {pPct > 0 && (
          <div
            className="h-full bg-[var(--color-success)]"
            style={{ width: `${pPct}%` }}
          />
        )}
        {tPct > 0 && (
          <div className="h-full bg-amber-400" style={{ width: `${tPct}%` }} />
        )}
        {fPct > 0 && (
          <div
            className="h-full bg-[var(--color-danger)]"
            style={{ width: `${fPct}%` }}
          />
        )}
      </div>
      <div className="mt-1.5 flex gap-3 text-xs text-[var(--color-text-muted)]">
        {passCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-[var(--color-success)]" />
            {passCount} aprobadas
          </span>
        )}
        {partialCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            {partialCount} parciales
          </span>
        )}
        {failCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-[var(--color-danger)]" />
            {failCount} suspensas
          </span>
        )}
      </div>
    </div>
  );
}

export function StudentPage() {
  const { githubLogin } = useParams();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudentSummary(githubLogin)
      .then(setSummary)
      .catch(() => setSummary(null));
  }, [githubLogin]);

  useEffect(() => {
    fetchStudentTasks(githubLogin, { page, pageSize: 10 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [githubLogin, page]);

  if (loading && !data) return <PageLoader />;

  const total = data?.total ?? 0;
  const repoSet = new Set(
    data?.items?.map((t) => t.repository_full_name) ?? [],
  );

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-indigo-600/20 text-xl font-bold text-indigo-400">
          {githubLogin.slice(0, 2).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]">
            {githubLogin}
          </h1>
          <a
            href={`https://github.com/${githubLogin}`}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Ver perfil en GitHub →
          </a>
        </div>
        <div className="ml-auto">
          <Link
            to="/students"
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            ← Todos los alumnos
          </Link>
        </div>
      </div>

      {/* Stats principales */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Mejor nota
          </p>
          <div className="mt-1">
            <ScoreDisplay score={summary?.best_score_overall ?? null} />
          </div>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Envíos totales
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-text)]">
            {total}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Completados
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-success)]">
            {summary?.completed_submissions ??
              data?.items?.filter((t) => t.status === "completed").length ??
              0}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Repositorios
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-text)]">
            {summary?.repos?.length ?? repoSet.size}
          </p>
        </div>
      </div>

      {/* Breakdown por repositorio */}
      {summary?.repos?.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            Resultados por repositorio
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {summary.repos.map((repo) => (
              <div
                key={repo.repository_full_name}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[var(--color-text)]">
                      {repo.repository_full_name}
                    </p>
                    <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
                      {repo.total_submissions} envío
                      {repo.total_submissions !== 1 ? "s" : ""} ·{" "}
                      {repo.completed_submissions} completado
                      {repo.completed_submissions !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <ScoreDisplay score={repo.best_score} size="md" />
                    {repo.best_task_id && (
                      <div className="mt-1">
                        <Link
                          to={`/tasks/${repo.best_task_id}`}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          {repo.best_pr_number
                            ? `PR #${repo.best_pr_number}`
                            : "Ver mejor evaluación"}{" "}
                          →
                        </Link>
                      </div>
                    )}
                  </div>
                </div>

                <VerdictBar
                  passCount={repo.pass_count}
                  partialCount={repo.partial_count}
                  failCount={repo.fail_count}
                />

                <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                  Última entrega: {formatDate(repo.last_submitted_at)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historial de evaluaciones */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
          Historial de evaluaciones
        </h2>

        {!data?.items?.length && !loading ? (
          <EmptyState
            title="Sin evaluaciones"
            description="Este alumno no tiene evaluaciones registradas."
          />
        ) : (
          <>
            <TaskTable tasks={data?.items ?? []} />

            {data && data.total_pages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-xs text-[var(--color-text-muted)]">
                  Página {data.page} de {data.total_pages} · {data.total}{" "}
                  evaluaciones
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page === 1 || loading}
                    onClick={() => {
                      setLoading(true);
                      setPage((p) => p - 1);
                    }}
                  >
                    ← Anterior
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= data.total_pages || loading}
                    onClick={() => {
                      setLoading(true);
                      setPage((p) => p + 1);
                    }}
                  >
                    Siguiente →
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
