import { Link, useNavigate } from "react-router-dom";
import { Badge } from "@/shared/ui/Badge";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { Eyebrow, Mono } from "@/shared/ui/Typography";
import { formatDate, formatScore } from "@/shared/lib/utils";
import { computeOverallScore, TASK_STATUS } from "@/entities/task/model";

const th =
  "px-5 py-3 text-left font-[family-name:var(--taro-font-mono)] text-[11px] " +
  "font-medium uppercase tracking-[0.14em] whitespace-nowrap text-[var(--taro-ink-dim)]";

export function TaskTable({ tasks }) {
  const navigate = useNavigate();
  if (!tasks?.length) return null;

  return (
    <div className="overflow-x-auto rounded-[var(--taro-radius-card)] border border-[var(--taro-line)] bg-[var(--taro-surface)]">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-[var(--taro-line)]">
            <th className={th}>Repositorio</th>
            <th className={`${th} hidden sm:table-cell`}>PR</th>
            <th className={th}>Estado</th>
            <th className={`${th} hidden md:table-cell`}>Puntuación</th>
            <th className={`${th} hidden lg:table-cell`}>Creado</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            const score = computeOverallScore(task.validations ?? []);
            const running = task.status === TASK_STATUS.RUNNING;

            return (
              <tr
                key={task.id}
                onClick={() => navigate(`/tasks/${task.id}`)}
                className="cursor-pointer border-b border-[var(--taro-line)] transition-[background-color] duration-[250ms] last:border-b-0 hover:bg-[var(--taro-raised)]"
              >
                <td className="px-5 py-4">
                  <Link
                    to={`/repos/${task.repository_full_name}`}
                    onClick={(e) => e.stopPropagation()}
                    className="font-[family-name:var(--taro-font-mono)] text-[13px] text-[var(--taro-ink)] transition-[color] duration-[250ms] hover:text-[var(--taro-brass)] hover:no-underline"
                  >
                    {task.repository_full_name}
                  </Link>
                </td>

                <td className="hidden px-5 py-4 sm:table-cell">
                  {task.pr_number ? (
                    <a
                      href={`https://github.com/${task.repository_full_name}/pull/${task.pr_number}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="font-[family-name:var(--taro-font-mono)] text-[13px] text-[var(--taro-brass)] hover:no-underline"
                    >
                      #{task.pr_number}
                    </a>
                  ) : (
                    <Mono className="text-[13px] text-[var(--taro-ink-dim)]">—</Mono>
                  )}
                </td>

                <td className="px-5 py-4">
                  <Badge kind="task" value={task.status} />
                  {running && (
                    <div className="mt-2 flex min-w-[110px] items-center gap-2">
                      <ProgressBar value={task.progress ?? 0} className="flex-1" />
                      <Mono className="w-8 text-right text-[11px] text-[var(--taro-ink-dim)]">
                        {task.progress ?? 0}%
                      </Mono>
                    </div>
                  )}
                </td>

                <td className="hidden px-5 py-4 md:table-cell">
                  <Mono className="text-[14px] text-[var(--taro-ink)]">
                    {formatScore(score)}
                  </Mono>
                </td>

                <td className="hidden px-5 py-4 lg:table-cell">
                  <Eyebrow className="normal-case tracking-[0.06em]">
                    {formatDate(task.created_at)}
                  </Eyebrow>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
