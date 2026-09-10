import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchRules } from "@/entities/rule/api";
import { fetchTasks } from "@/entities/task/api";
import { fetchRepoContributors } from "@/entities/contributor/api";
import { RuleList } from "@/widgets/RuleList/RuleList";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import ContributorTable from "@/widgets/ContributorTable/ContributorTable";
import { RepoSettingsForm } from "@/features/settings/RepoSettingsForm";
import { TriggerValidation } from "@/features/tasks/TriggerValidation";
import { PageLoader } from "@/shared/ui/Spinner";
import { Badge } from "@/shared/ui/Badge";
import { Card } from "@/shared/ui/Card";
import { PageTitle, SectionTitle, Eyebrow, Body, Mono } from "@/shared/ui/Typography";
import { clsx } from "@/shared/lib/utils";

const TABS = ["Reglas", "Evaluaciones", "Colaboradores", "Configuración"];

const MAX_RULES = 10;

export function RepoDetailPage() {
  const { owner, repo } = useParams();
  const [tab, setTab] = useState("Reglas");
  const [rules, setRules] = useState([]);
  const [tasks, setTasks] = useState(null);
  const [contributors, setContributors] = useState([]);
  const [contributorsLoading, setContributorsLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRules(owner, repo, { pageSize: MAX_RULES }),
      fetchTasks({ repositoryFullName: `${owner}/${repo}`, pageSize: 10 }),
    ])
      .then(([r, t]) => {
        setRules(r.items ?? []);
        setTasks(t);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [owner, repo]);

  useEffect(() => {
    if (tab !== "Colaboradores") return;
    fetchRepoContributors(owner, repo)
      .then((data) => setContributors(data ?? []))
      .catch(() => setContributors([]))
      .finally(() => setContributorsLoading(false));
  }, [tab, owner, repo]);

  function handleRuleCreated(rule) {
    setRules((prev) => [...prev, rule]);
  }

  function handleRulesImported(newRules) {
    setRules((prev) => [...prev, ...newRules]);
  }

  function handleRuleDeleted(ruleId) {
    setRules((prev) => prev.filter((r) => r.id !== ruleId));
  }

  function handleRulesDeletedMany(ids) {
    setRules((prev) => prev.filter((r) => !ids.includes(r.id)));
  }

  function handleRuleUpdated(updated) {
    setRules((prev) => prev.map((r) => r.id === updated.id ? updated : r));
  }

  if (loading) return <PageLoader />;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col px-8 py-10">
      {/* Breadcrumb */}
      <nav className="mb-5 flex items-center gap-2 text-[13px] text-[var(--taro-ink-dim)]">
        <Link to="/repos" className="text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-ink)] hover:no-underline">
          Repositorios
        </Link>
        <span>/</span>
        <Mono className="text-[12.5px] text-[var(--taro-ink-dim)]">{owner}</Mono>
        <span>/</span>
        <Mono className="text-[12.5px] text-[var(--taro-ink)]">{repo}</Mono>
      </nav>

      {/* Header */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <PageTitle className="truncate">{repo}</PageTitle>
            <a
              href={`https://github.com/${owner}/${repo}`}
              target="_blank"
              rel="noreferrer"
              title="Ver en GitHub"
              className="text-[var(--taro-ink-dim)] transition-[color] duration-[250ms] hover:text-[var(--taro-brass)]"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23A11.52 11.52 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.29-1.552 3.297-1.23 3.297-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/>
              </svg>
            </a>
          </div>
          <Mono className="mt-2 block text-[12.5px] text-[var(--taro-ink-dim)]">
            {owner}/{repo}
          </Mono>
        </div>
        <TriggerValidation owner={owner} repo={repo} />
      </div>

      {/* Tabs */}
      <div className="mb-8 flex gap-6 border-b border-[var(--taro-line)]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              if (t === "Colaboradores" && tab !== "Colaboradores")
                setContributorsLoading(true);
              setTab(t);
            }}
            className={clsx(
              "-mb-px flex cursor-pointer items-center gap-2 border-b-2 pb-2.5 text-[14px] whitespace-nowrap",
              "transition-[color,border-color] duration-[250ms]",
              tab === t
                ? "border-[var(--taro-brass)] text-[var(--taro-ink)]"
                : "border-transparent text-[var(--taro-ink-dim)] hover:text-[var(--taro-ink)]",
            )}
          >
            {t}
            {t === "Reglas" && (
              <Badge kind="tone" value={rules.length >= MAX_RULES ? "partial" : "neutral"}>
                {rules.length}/{MAX_RULES}
              </Badge>
            )}
            {t === "Evaluaciones" && tasks?.total > 0 && (
              <Badge kind="tone" value="neutral">{tasks.total}</Badge>
            )}
            {t === "Colaboradores" && contributors.length > 0 && (
              <Badge kind="tone" value="neutral">{contributors.length}</Badge>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "Reglas" && (
        <RuleList
          rules={rules}
          owner={owner}
          repo={repo}
          maxRules={MAX_RULES}
          onCreated={handleRuleCreated}
          onUpdated={handleRuleUpdated}
          onDeleted={handleRuleDeleted}
          onImported={handleRulesImported}
        />
      )}

      {tab === "Evaluaciones" && (
        <div>
          {tasks?.items?.length ? (
            <TaskTable tasks={tasks.items} />
          ) : (
            <Card className="text-center">
              <Body muted>
                No hay evaluaciones para este repositorio. Inicia una con el
                botón de arriba.
              </Body>
            </Card>
          )}
        </div>
      )}

      {tab === "Colaboradores" && (
        <div>
          <Body muted className="mb-5">
            Colaboradores que han abierto pull requests en este repositorio.
          </Body>
          <ContributorTable contributors={contributors} loading={contributorsLoading} />
        </div>
      )}

      {tab === "Configuración" && (
        <Card>
          <SectionTitle className="mb-6">
            Configuración del repositorio
          </SectionTitle>
          <RepoSettingsForm owner={owner} repo={repo} />
        </Card>
      )}
    </div>
  );
}
