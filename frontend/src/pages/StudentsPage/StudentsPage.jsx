import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchAllStudents } from "../../entities/student/api";
import { PageLoader } from "../../shared/ui/Spinner";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Badge } from "../../shared/ui/Badge";
import { formatDate, statusColor } from "../../shared/lib/utils";

function scoreColor(score) {
  if (score === null || score === undefined) return "muted";
  if (score >= 8) return "success";
  if (score >= 5) return "warning";
  return "danger";
}

function ScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return <span className="text-[var(--color-text-muted)]">—</span>;
  }
  const color = scoreColor(score);
  const colorMap = {
    success: "text-[var(--color-success)] bg-emerald-500/10",
    warning: "text-amber-400 bg-amber-400/10",
    danger: "text-[var(--color-danger)] bg-red-500/10",
    muted: "text-[var(--color-text-muted)] bg-[var(--color-surface-2)]",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums ${colorMap[color]}`}
    >
      {score.toFixed(1)}/10
    </span>
  );
}

const STATUS_LABEL = {
  completed: "Completada",
  failed: "Fallida",
  running: "Ejecutando",
  pending: "Pendiente",
};

export function StudentsPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchAllStudents()
      .then(setStudents)
      .catch(() => setStudents([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;

  const filtered = (students ?? []).filter((s) =>
    s.pr_author.toLowerCase().includes(search.toLowerCase()),
  );

  const total = students?.length ?? 0;
  const withScore = students?.filter((s) => s.avg_score !== null).length ?? 0;
  const avgScore =
    withScore > 0
      ? students.reduce((sum, s) => sum + (s.avg_score ?? 0), 0) / withScore
      : null;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">Alumnos</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Vista global de todos los alumnos que han abierto PRs en tus
          repositorios.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Total alumnos
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-text)]">
            {total}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Con evaluación
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-success)]">
            {withScore}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Nota media
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-text)]">
            {avgScore !== null ? avgScore.toFixed(1) : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Sin completar
          </p>
          <p className="mt-1 text-3xl font-bold text-amber-400">
            {total - withScore}
          </p>
        </div>
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          placeholder="Buscar alumno por nombre…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] placeholder-[var(--color-text-muted)] outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </div>

      {/* Table */}
      {!filtered.length ? (
        <EmptyState
          title={search ? "Sin resultados" : "Sin alumnos todavía"}
          description={
            search
              ? "No hay alumnos que coincidan con la búsqueda."
              : "Los alumnos aparecerán aquí cuando abran su primera PR."
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Alumno</th>
                <th className="px-4 py-3 text-center">Nota media</th>
                <th className="px-4 py-3 text-center hidden sm:table-cell">
                  Envíos
                </th>
                <th className="px-4 py-3 text-center hidden md:table-cell">
                  Completados
                </th>
                <th className="px-4 py-3 text-center hidden md:table-cell">
                  Repos
                </th>
                <th className="px-4 py-3 hidden lg:table-cell">
                  Último estado
                </th>
                <th className="px-4 py-3 hidden lg:table-cell">
                  Última entrega
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {filtered.map((s) => (
                <tr
                  key={s.pr_author}
                  onClick={() => navigate(`/students/${s.pr_author}`)}
                  className="cursor-pointer transition-colors hover:bg-[var(--color-surface-2)]"
                >
                  {/* Alumno */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600/20 text-xs font-semibold text-indigo-400">
                        {s.pr_author.slice(0, 2).toUpperCase()}
                      </div>
                      <span className="font-medium text-[var(--color-text)]">
                        {s.pr_author}
                      </span>
                    </div>
                  </td>

                  {/* Nota media */}
                  <td className="px-4 py-3 text-center">
                    <ScoreBadge score={s.avg_score} />
                  </td>

                  {/* Envíos */}
                  <td className="px-4 py-3 text-center hidden sm:table-cell">
                    <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-[var(--color-surface-2)] px-1.5 text-xs font-medium text-[var(--color-text-muted)]">
                      {s.total_submissions}
                    </span>
                  </td>

                  {/* Completados */}
                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    <span className="text-[var(--color-success)] font-medium">
                      {s.completed_submissions}
                    </span>
                    <span className="text-[var(--color-text-muted)]">
                      /{s.total_submissions}
                    </span>
                  </td>

                  {/* Repos */}
                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    <span className="text-[var(--color-text-muted)]">
                      {s.repo_count}
                    </span>
                  </td>

                  {/* Último estado */}
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {s.last_status ? (
                      <Badge color={statusColor(s.last_status)}>
                        {STATUS_LABEL[s.last_status] ?? s.last_status}
                      </Badge>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>

                  {/* Última entrega */}
                  <td className="px-4 py-3 text-[var(--color-text-muted)] hidden lg:table-cell">
                    {formatDate(s.last_submitted_at)}
                  </td>

                  {/* Acción */}
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/students/${s.pr_author}`}
                      className="text-xs font-medium text-indigo-400 transition-colors hover:text-indigo-300"
                    >
                      Ver detalle →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
