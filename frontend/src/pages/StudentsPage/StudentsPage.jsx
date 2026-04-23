import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchAllContributors } from "@/entities/contributor/api";
import { PageLoader } from "@/shared/ui/Spinner";
import { EmptyState } from "@/shared/ui/EmptyState";
import { Badge } from "@/shared/ui/Badge";
import { formatDate, statusColor } from "@/shared/lib/utils";

const STATUS_LABEL = {
  completed: "Completada",
  failed: "Fallida",
  running: "Ejecutando",
  pending: "Pendiente",
};

export function StudentsPage() {
  const navigate = useNavigate();
  const [contributors, setContributors] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchAllContributors()
      .then(setContributors)
      .catch(() => setContributors([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;

  const filtered = (contributors ?? []).filter((s) =>
    s.pr_author.toLowerCase().includes(search.toLowerCase()),
  );

  const total = contributors?.length ?? 0;
  const withCompleted =
    contributors?.filter((s) => s.completed_submissions > 0).length ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          Colaboradores
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Vista global de todos los colaboradores que han abierto PRs en tus
          repositorios.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Total colaboradores
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-text)]">
            {total}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Con evaluación completada
          </p>
          <p className="mt-1 text-3xl font-bold text-[var(--color-success)]">
            {withCompleted}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
            Sin completar
          </p>
          <p className="mt-1 text-3xl font-bold text-amber-400">
            {total - withCompleted}
          </p>
        </div>
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          placeholder="Buscar colaborador por nombre…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text)] placeholder-[var(--color-text-muted)] outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </div>

      {/* Table */}
      {!filtered.length ? (
        <EmptyState
          title={search ? "Sin resultados" : "Sin colaboradores todavía"}
          description={
            search
              ? "No hay colaboradores que coincidan con la búsqueda."
              : "Los colaboradores aparecerán aquí cuando abran su primera PR."
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-4 py-3">Colaborador</th>
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
                  onClick={() => navigate(`/contributors/${s.pr_author}`)}
                  className="cursor-pointer transition-colors hover:bg-[var(--color-surface-2)]"
                >
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

                  <td className="px-4 py-3 text-center hidden sm:table-cell">
                    <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-[var(--color-surface-2)] px-1.5 text-xs font-medium text-[var(--color-text-muted)]">
                      {s.total_submissions}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    <span className="text-[var(--color-success)] font-medium">
                      {s.completed_submissions}
                    </span>
                    <span className="text-[var(--color-text-muted)]">
                      /{s.total_submissions}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    <span className="text-[var(--color-text-muted)]">
                      {s.repo_count}
                    </span>
                  </td>

                  <td className="px-4 py-3 hidden lg:table-cell">
                    {s.last_status ? (
                      <Badge color={statusColor(s.last_status)}>
                        {STATUS_LABEL[s.last_status] ?? s.last_status}
                      </Badge>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-[var(--color-text-muted)] hidden lg:table-cell">
                    {formatDate(s.last_submitted_at)}
                  </td>

                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/contributors/${s.pr_author}`}
                      className="text-xs font-medium text-indigo-400 transition-colors hover:text-indigo-300"
                      onClick={(e) => e.stopPropagation()}
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
