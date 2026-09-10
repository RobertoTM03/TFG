import { useEffect, useState } from "react";
import { fetchTasks } from "@/entities/task/api";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import { PageLoader } from "@/shared/ui/Spinner";
import { Button } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader, Eyebrow, Body } from "@/shared/ui/Typography";

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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-8 py-10">
      <PageHeader eyebrow="Todos los repositorios" title="Evaluaciones">
        <Body muted className="mt-3">
          Historial de todas las validaciones realizadas.
        </Body>
      </PageHeader>

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
              <Eyebrow>
                Página {data.page} de {data.total_pages} · {data.total} evaluaciones
              </Eyebrow>
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
                  Anterior
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
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
