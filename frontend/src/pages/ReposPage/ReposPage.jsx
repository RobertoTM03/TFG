import { useEffect, useState } from "react";
import { fetchRepos, fetchAppInfo } from "@/entities/repo/api";
import { getInstallUrl } from "@/entities/repo/model";
import { RepoCard } from "@/widgets/RepoCard/RepoCard";
import { PageLoader } from "@/shared/ui/Spinner";
import { Button } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";

export function ReposPage() {
  const [repos, setRepos] = useState(null);
  const [appInfo, setAppInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchRepos().catch((e) => {
        setError(e.message);
        return [];
      }),
      fetchAppInfo().catch(() => null),
    ]).then(([r, info]) => {
      setRepos(r);
      setAppInfo(info);
      setLoading(false);
    });
  }, []);

  if (loading) return <PageLoader />;

  const installUrl = appInfo?.app_slug ? getInstallUrl(appInfo.app_slug) : null;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]">
            Repositorios
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Repositorios con la GitHub App instalada
          </p>
        </div>
        {installUrl && (
          <a href={installUrl} target="_blank" rel="noopener noreferrer">
            <Button variant="secondary" size="sm">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clipRule="evenodd"
                />
              </svg>
              Instalar en más repos
            </Button>
          </a>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {!repos?.length ? (
        <EmptyState
          title="No hay repositorios conectados"
          description="Instala la GitHub App en tus repositorios para empezar a usarlos."
          action={
            installUrl ? (
              <a href={installUrl} target="_blank" rel="noopener noreferrer">
                <Button>Instalar GitHub App</Button>
              </a>
            ) : null
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {repos.map((repo) => (
            <RepoCard key={repo.full_name} repo={repo} />
          ))}
        </div>
      )}
    </div>
  );
}
