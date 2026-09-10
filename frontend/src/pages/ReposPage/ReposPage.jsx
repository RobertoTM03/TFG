import { useEffect, useState } from "react";
import { fetchRepos, fetchAppInfo } from "@/entities/repo/api";
import { getInstallUrl } from "@/entities/repo/model";
import { RepoCard } from "@/widgets/RepoCard/RepoCard";
import { PageLoader } from "@/shared/ui/Spinner";
import { EmptyState } from "@/shared/ui/EmptyState";
import { Button } from "@/shared/ui/Button";
import { PageHeader, Body } from "@/shared/ui/Typography";

const GITHUB_ICON = (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
  </svg>
);

export function ReposPage() {
  const [repos, setRepos] = useState(null);
  const [appInfo, setAppInfo] = useState(null);
const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = (showLoader = false) => {
    if (showLoader) setLoading(true);
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
  };

  useEffect(() => {
    loadData(true);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") loadData();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  if (loading) return <PageLoader />;

  const installUrl = appInfo?.app_slug ? getInstallUrl(appInfo.app_slug) : null;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-8 py-10">
      <PageHeader
        eyebrow="Conectados"
        title="Repositorios"
        action={
          installUrl ? (
            <a href={installUrl} target="_blank" rel="noopener noreferrer" className="hover:no-underline">
              <Button variant="github" size="sm" className="no-underline">
              {GITHUB_ICON}
              Instalar GitHub App
            </Button>
            </a>
          ) : null
        }
      >
        <Body muted className="mt-3">
          Repositorios de GitHub conectados a Taro.
        </Body>
      </PageHeader>

      {error && (
        <div className="rounded-[var(--taro-radius-row)] border border-[var(--taro-incorrect-line)] bg-[var(--taro-incorrect-bg)] px-4 py-3 text-[13.5px] text-[var(--taro-incorrect-ink)]">
          {error}
        </div>
      )}

{!repos?.length ? (
        <EmptyState
          title="No hay repositorios conectados"
          description="Instala la GitHub App en tus repositorios para empezar a usarlos."
          action={
            installUrl ? (
              <a href={installUrl} target="_blank" rel="noopener noreferrer" className="hover:no-underline">
                <Button variant="github" size="sm">
                  {GITHUB_ICON}
                  Instalar GitHub App
                </Button>
              </a>
            ) : null
          }
        />
      ) : (
        <>
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}
          >
            {repos.map((repo) => (
              <RepoCard key={repo.full_name} repo={repo} />
            ))}
          </div>

        </>
      )}
    </div>
  );
}
