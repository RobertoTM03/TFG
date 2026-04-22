import { Link, useNavigate } from "react-router-dom";
import { Badge } from "@/shared/ui/Badge";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { formatDate } from "@/shared/lib/utils";
import { statusColor } from "@/shared/lib/utils";

const STATUS_LABELS = {
  pending: "Pendiente",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Fallido",
};

export function TaskTable({ tasks }) {
  const navigate = useNavigate();
  if (!tasks?.length) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Repositorio
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Estado
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] hidden md:table-cell">
              Progreso
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] hidden lg:table-cell">
              Creado
            </th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)] bg-[var(--color-surface)]">
          {tasks.map((task) => (
            <tr
              key={task.id}
              onClick={() => navigate(`/tasks/${task.id}`)}
              className="cursor-pointer transition-colors hover:bg-[var(--color-surface-2)]"
            >
              <td className="px-4 py-3">
                <span className="font-medium text-[var(--color-text)]">
                  {task.repository_full_name}
                </span>
              </td>
              <td className="px-4 py-3">
                <Badge color={statusColor(task.status)}>
                  {STATUS_LABELS[task.status] ?? task.status}
                </Badge>
              </td>
              <td className="px-4 py-3 hidden md:table-cell">
                <div className="flex items-center gap-2 min-w-[100px]">
                  <ProgressBar
                    value={task.progress ?? 0}
                    color={
                      task.status === "failed"
                        ? "danger"
                        : task.status === "completed"
                          ? "success"
                          : "primary"
                    }
                    className="flex-1"
                  />
                  <span className="text-xs text-[var(--color-text-muted)] w-8 text-right">
                    {task.progress ?? 0}%
                  </span>
                </div>
              </td>
              <td className="px-4 py-3 text-[var(--color-text-muted)] hidden lg:table-cell">
                {formatDate(task.created_at)}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/tasks/${task.id}`}
                  className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Ver →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
