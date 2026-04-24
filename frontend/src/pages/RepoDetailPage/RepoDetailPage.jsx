import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchRules } from "@/entities/rule/api";
import { fetchTasks } from "@/entities/task/api";
import { fetchRepoContributors } from "@/entities/contributor/api";
import { RuleList } from "@/widgets/RuleList/RuleList";
import { TaskTable } from "@/widgets/TaskTable/TaskTable";
import ContributorTable from "@/widgets/ContributorTable/ContributorTable";
import { RuleForm } from "@/features/rules/RuleForm";
import { RuleImportExport } from "@/features/rules/RuleImportExport";
import { RepoSettingsForm } from "@/features/settings/RepoSettingsForm";
import { TriggerValidation } from "@/features/tasks/TriggerValidation";
import { PageLoader } from "@/shared/ui/Spinner";
import { Badge } from "@/shared/ui/Badge";
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

  if (loading) return <PageLoader />;

  return (
    <div className="flex flex-col gap-0 p-6 max-w-5xl mx-auto w-full">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] mb-5">
        <Link
          to="/repos"
          className="hover:text-[var(--color-text)] transition-colors"
        >
          Repositorios
        </Link>
        <span>/</span>
        <span>{owner}</span>
        <span>/</span>
        <span className="text-[var(--color-text)] font-medium">{repo}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]">
            {repo}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {owner}/{repo}
          </p>
        </div>
        <TriggerValidation owner={owner} repo={repo} />
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[var(--color-border)] mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              if (t === "Colaboradores" && tab !== "Colaboradores")
                setContributorsLoading(true);
              setTab(t);
            }}
            className={clsx(
              "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              tab === t
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]",
            )}
          >
            {t}
            {t === "Reglas" && (
              <Badge
                color={rules.length >= MAX_RULES ? "warning" : "muted"}
                className="ml-2"
              >
                {rules.length}/{MAX_RULES}
              </Badge>
            )}
            {t === "Evaluaciones" && tasks?.total > 0 && (
              <Badge color="muted" className="ml-2">
                {tasks.total}
              </Badge>
            )}
            {t === "Colaboradores" && contributors.length > 0 && (
              <Badge color="muted" className="ml-2">
                {contributors.length}
              </Badge>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "Reglas" && (
        <div className="flex flex-col gap-6">
          {rules.length < MAX_RULES && (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
              <h2 className="text-sm font-semibold text-[var(--color-text)] mb-4">
                Añadir regla de validación
              </h2>
              <RuleForm
                owner={owner}
                repo={repo}
                onCreated={handleRuleCreated}
              />
            </div>
          )}
          {rules.length >= MAX_RULES && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
              Límite de {MAX_RULES} reglas alcanzado. Elimina alguna para poder
              añadir más.
            </div>
          )}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--color-text)]">
                Reglas actuales ({rules.length})
              </h2>
              <RuleImportExport
                owner={owner}
                repo={repo}
                rules={rules}
                onImported={handleRulesImported}
              />
            </div>
          </div>

          {rules.length > 0 ? (
            <div>
              <RuleList
                rules={rules}
                owner={owner}
                repo={repo}
                onDeleted={handleRuleDeleted}
              />
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[var(--color-border)] p-10 text-center">
              <p className="text-sm text-[var(--color-text-muted)]">
                No hay reglas definidas. Añade la primera usando el formulario
                de arriba.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "Evaluaciones" && (
        <div>
          {tasks?.items?.length ? (
            <TaskTable tasks={tasks.items} />
          ) : (
            <div className="rounded-xl border border-dashed border-[var(--color-border)] p-10 text-center">
              <p className="text-sm text-[var(--color-text-muted)]">
                No hay evaluaciones para este repositorio. Inicia una con el
                botón de arriba.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "Colaboradores" && (
        <div>
          <p className="mb-4 text-sm text-[var(--color-text-muted)]">
            Colaboradores que han abierto pull requests en este repositorio.
          </p>
          <ContributorTable contributors={contributors} loading={contributorsLoading} />
        </div>
      )}

      {tab === "Configuración" && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text)] mb-4">
            Configuración del repositorio
          </h2>
          <RepoSettingsForm owner={owner} repo={repo} />
        </div>
      )}
    </div>
  );
}
