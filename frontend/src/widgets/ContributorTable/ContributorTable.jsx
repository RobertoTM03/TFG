import { Link, useNavigate } from "react-router-dom";
import { Badge } from "../../shared/ui/Badge";
import { formatDate, statusColor } from "../../shared/lib/utils";

const STATUS_LABEL = {
  completed: "Completada",
  failed: "Fallida",
  running: "Ejecutando",
  pending: "Pendiente",
};

/**
 * Table of contributors derived from pr_author aggregation.
 *
 * @param {{ contributors: Array, loading?: boolean }} props
 */
export default function ContributorTable({ contributors = [], loading = false }) {
  const navigate = useNavigate();
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-primary)] border-t-transparent" />
      </div>
    );
  }

  if (!contributors.length) {
    return (
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
        <p className="mt-2 font-medium text-[var(--color-text)]">
          Sin contribuciones todavía
        </p>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Los colaboradores aparecerán aquí cuando abran su primera PR.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
            <th className="px-4 py-3">Colaborador</th>
            <th className="px-4 py-3 text-center">Envíos</th>
            <th className="px-4 py-3">Último estado</th>
            <th className="hidden px-4 py-3 lg:table-cell">Última contribución</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)]">
          {contributors.map((s) => (
            <tr
              key={s.pr_author}
              onClick={() => navigate(`/contributors/${s.pr_author}`)}
              className="cursor-pointer transition-colors hover:bg-[var(--color-surface-2)]"
            >
              {/* Colaborador */}
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

              {/* Envíos */}
              <td className="px-4 py-3 text-center">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-xs font-medium text-[var(--color-text-muted)]">
                  {s.submissions}
                </span>
              </td>

              {/* Último estado */}
              <td className="px-4 py-3">
                {s.last_status ? (
                  <Badge color={statusColor(s.last_status)}>
                    {STATUS_LABEL[s.last_status] ?? s.last_status}
                  </Badge>
                ) : (
                  <span className="text-[var(--color-text-muted)]">—</span>
                )}
              </td>

              {/* Última contribución */}
              <td className="hidden px-4 py-3 text-[var(--color-text-muted)] lg:table-cell">
                {formatDate(s.last_submitted_at)}
              </td>

              {/* Acción */}
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/contributors/${s.pr_author}`}
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
  );
}
