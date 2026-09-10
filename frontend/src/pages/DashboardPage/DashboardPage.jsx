import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ActivityChart } from "@/widgets/ActivityChart/ActivityChart";
import { useAuth } from "@/features/auth/AuthContext";
import { fetchRepos } from "@/entities/repo/api";
import { fetchTasks } from "@/entities/task/api";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import { PageLoader } from "@/shared/ui/Spinner";
import { Button } from "@/shared/ui/Button";
import { Card, CardGrid, CardCell } from "@/shared/ui/Card";
import { PageHeader, SectionTitle, Eyebrow, Body, Mono } from "@/shared/ui/Typography";

function Stat({ label, value, sub, to }) {
  const inner = (
    <CardCell interactive={!!to} className="h-full">
      <Mono className="block text-[30px] leading-none text-[var(--taro-ink)]">
        {value ?? "—"}
      </Mono>
      <Eyebrow className="mt-3 block">{label}</Eyebrow>
      <p className="mt-1 min-h-[20px] text-[12px] leading-[20px] text-[var(--taro-ink-dim)]">
        {sub ?? ""}
      </p>
    </CardCell>
  );
  return to ? (
    <Link to={to} className="hover:no-underline">
      {inner}
    </Link>
  ) : (
    inner
  );
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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-8 py-10">
      <PageHeader eyebrow="Resumen" title={`Hola, ${user?.github_login ?? ""}`}>
        <Body muted className="mt-3">
          Tu actividad reciente en Taro.
        </Body>
      </PageHeader>

      <CardGrid columns={2}>
        <Stat
          label="Repositorios"
          value={repos.length || null}
          sub="con la GitHub App"
          to="/repos"
        />
        <Stat
          label="Evaluaciones totales"
          value={total || null}
          sub="en todos los repos"
          to="/tasks"
        />
        <Stat
          label="Porcentaje completado"
          value={completedPct != null ? `${completedPct}%` : null}
          sub={`sobre las últimas ${allTasks.length}`}
        />
        <Stat
          label="Pendiente de ejecución"
          value={pendingCount}
          sub="en curso o en cola"
        />
      </CardGrid>

      {allTasks.length > 0 && <ActivityChart tasks={allTasks} repos={repos} />}

      <div>
        <div className="mb-5 flex items-center justify-between gap-4">
          <SectionTitle>Últimas evaluaciones</SectionTitle>
          <Link to="/tasks" className="hover:no-underline">
            <Button variant="ghost" size="sm">
              Ver todas
            </Button>
          </Link>
        </div>
        {tasks?.items?.length ? (
          <TaskTable tasks={tasks.items} />
        ) : (
          <Card className="text-center">
            <Body muted>
              No hay evaluaciones todavía.{" "}
              <Link to="/repos">Ve a un repositorio</Link> para iniciar la
              primera.
            </Body>
          </Card>
        )}
      </div>
    </div>
  );
}
