import { Link } from "react-router-dom";
import { Badge } from "@/shared/ui/Badge";

export function RepoCard({ repo }) {
  const [owner, name] = repo.full_name.split("/");

  return (
    <Link
      to={`/repos/${owner}/${name}`}
      className="group flex flex-col rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all hover:border-indigo-500/50 hover:bg-[var(--color-surface-2)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 text-[var(--color-text-muted)]"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
            <span className="text-xs text-[var(--color-text-muted)] truncate">
              {owner}
            </span>
          </div>
          <h3 className="font-semibold text-[var(--color-text)] group-hover:text-indigo-400 transition-colors truncate">
            {name}
          </h3>
          {repo.description && (
            <p className="mt-1.5 text-sm text-[var(--color-text-muted)] line-clamp-2">
              {repo.description}
            </p>
          )}
        </div>
        {repo.private && (
          <Badge color="muted">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3 w-3"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                clipRule="evenodd"
              />
            </svg>
            Privado
          </Badge>
        )}
      </div>

      <div className="mt-auto pt-4 flex items-center gap-3">
        {repo.language && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
            <span className="h-2 w-2 rounded-full bg-indigo-400" />
            {repo.language}
          </div>
        )}
        <div className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-3.5 w-3.5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          {repo.stargazers_count}
        </div>
        <div className="ml-auto">
          <span className="text-xs text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
            Gestionar →
          </span>
        </div>
      </div>
    </Link>
  );
}
