import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ActivityChart } from "@/widgets/ActivityChart/ActivityChart";
import { useAuth } from "@/features/auth/AuthContext";
import { fetchRepos } from "@/entities/repo/api";
import { fetchTasks } from "@/entities/task/api";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import { PageLoader } from "@/shared/ui/Spinner";
import { Button } from "@/shared/ui/Button";

function StatCard({ label, value, sub, to }) {
  const inner = (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 hover:border-indigo-500/40 transition-colors">
      <p className="text-3xl font-bold text-[var(--color-text)] tabular-nums">
        {value ?? "—"}
      </p>
      <p className="mt-1 text-sm font-medium text-[var(--color-text)]">
        {label}
      </p>
      {sub && (
        <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{sub}</p>
      )}
    </div>
  );
  return to ? <Link to={to}>{inner}</Link> : inner;
}

export function DashboardPage() {
  const { user } = useAuth();
  const [repos, setRepos] = useState([]);
  const [tasks, setTasks] = useState(null);
  const [allTasks, setAllTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRepos().catch(() => []),
      fetchTasks({ pageSize: 5 }).catch(() => null),
      fetchTasks({ pageSize: 50 }).catch(() => null),
    ]).then(([r, t5, t50]) => {
      setRepos(r ?? []);
      setTasks(t5);
      setAllTasks(t50?.items ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) return <PageLoader />;

  const total = tasks?.total ?? 0;
  const completedCount = allTasks.filter(
    (t) => t.status === "completed",
  ).length;
  const pendingCount = allTasks.filter(
    (t) => t.status === "pending" || t.status === "running",
  ).length;
  const completedPct =
    allTasks.length > 0
      ? Math.round((completedCount / allTasks.length) * 100)
      : null;

  return (
    <div className="flex flex-col gap-8 p-6 max-w-5xl mx-auto w-full">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          Bienvenido, {user?.github_login}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Resumen de tu actividad en CodeReview AI
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Repositorios"
          value={repos.length || null}
          sub="con la GitHub App"
          to="/repos"
        />
        <StatCard
          label="Evaluaciones totales"
          value={total || null}
          sub="en todos los repos"
          to="/tasks"
        />
        <StatCard
          label="Porcentaje completado"
          value={completedPct != null ? `${completedPct}%` : null}
          sub={`sobre las últimas ${allTasks.length}`}
        />
        <StatCard
          label="Pendiente de ejecución"
          value={pendingCount}
          sub="en curso o en cola"
        />
      </div>

      {allTasks.length > 0 && <ActivityChart tasks={allTasks} repos={repos} />}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-[var(--color-text)]">
            Últimas evaluaciones
          </h2>
          <Link to="/tasks">
            <Button variant="ghost" size="sm">
              Ver todas →
            </Button>
          </Link>
        </div>
        {tasks?.items?.length ? (
          <TaskTable tasks={tasks.items} />
        ) : (
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
            <p className="text-sm text-[var(--color-text-muted)]">
              No hay evaluaciones todavía.{" "}
              <Link to="/repos" className="text-indigo-400 hover:underline">
                Ve a un repositorio
              </Link>{" "}
              para iniciar la primera.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
