import { useEffect, useState } from "react";
import { fetchTasks } from "@/entities/task/api";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import { PageLoader } from "@/shared/ui/Spinner";
import { Button } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";

export function TasksPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks({ page, pageSize: 10 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [page]);

  if (loading && !data) return <PageLoader />;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          Evaluaciones
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Historial de todas las validaciones realizadas
        </p>
      </div>

      {!data?.items?.length && !loading ? (
        <EmptyState
          title="Sin evaluaciones todavía"
          description="Las evaluaciones aparecen aquí cuando se lanzan manualmente o a través de un pull request."
        />
      ) : (
        <>
          <TaskTable tasks={data?.items ?? []} />

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between">
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
  );
}
