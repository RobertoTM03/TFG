import { Link } from "react-router-dom";
import { Badge } from "@/shared/ui/Badge";

const languageColors = {
  TypeScript: "#3178c6",
  JavaScript: "#f1e05a",
  Python: "#3572A5",
  Java: "#b07219",
  Go: "#00ADD8",
  Rust: "#dea584",
  Ruby: "#701516",
  "C++": "#f34b7d",
  C: "#555555",
  "C#": "#178600",
  PHP: "#4F5D95",
  Swift: "#F05138",
  Kotlin: "#A97BFF",
  React: "#61dafb",
};

function getLanguageColor(lang) {
  return languageColors[lang] ?? "#8b949e";
}

export function RepoCard({ repo }) {
  const [owner, name] = repo.full_name.split("/");

  return (
    <Link
      to={`/repos/${owner}/${name}`}
      className="group flex items-center gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 transition-all hover:border-indigo-500/30 hover:bg-[var(--color-surface-2)]"
    >
      {/* Language color dot */}
      <div
        className="h-3 w-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: repo.language ? getLanguageColor(repo.language) : "#8b949e" }}
      />

      {/* Repo info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-[var(--color-text)] group-hover:text-indigo-400 transition-colors">
            {repo.full_name}
          </span>
          <Badge color={repo.private ? "muted" : "primary"}>
            {repo.private ? "Privado" : "Público"}
          </Badge>
          <Badge color={repo.pr_evaluation_enabled ? "success" : "muted"}>
            {repo.pr_evaluation_enabled ? "Evaluación activa" : "Evaluación desactivada"}
          </Badge>
        </div>

        <div className="mt-1.5 flex items-center gap-4 flex-wrap">
          {repo.language && (
            <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: getLanguageColor(repo.language) }}
              />
              {repo.language}
            </span>
          )}
          <span className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            {repo.stargazers_count}
          </span>
          {repo.description && (
            <span className="text-xs text-[var(--color-text-muted)] truncate max-w-xs">
              {repo.description}
            </span>
          )}
        </div>
      </div>

      {/* Configure indicator */}
      <div className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-sm text-[var(--color-text-muted)] group-hover:border-indigo-500/50 group-hover:text-indigo-400 transition-all">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
        </svg>
        Configurar
      </div>
    </Link>
  );
}
