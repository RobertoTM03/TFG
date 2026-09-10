import { Link } from "react-router-dom";
import { Badge } from "@/shared/ui/Badge";
import { Card } from "@/shared/ui/Card";
import { SectionTitle, Mono, Eyebrow } from "@/shared/ui/Typography";

export function RepoCard({ repo }) {
  const [owner, name] = repo.full_name.split("/");

  return (
    <Card
      as={Link}
      to={`/repos/${owner}/${name}`}
      interactive
      className="flex flex-col gap-4 no-underline hover:no-underline"
    >
      <div className="min-w-0">
        <Mono className="block text-[11.5px] text-[var(--taro-ink-dim)]">
          {owner}
        </Mono>
        <SectionTitle className="mt-1 truncate text-[21px]">{name}</SectionTitle>
      </div>

      <p className="min-h-[44px] text-[13.5px] leading-[1.6] text-[var(--taro-ink-muted)] [text-wrap:pretty]">
        {repo.description ?? ""}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        {repo.last_status ? (
          <Badge kind="task" value={repo.last_status} />
        ) : (
          <Badge kind="tone" value="neutral">
            Sin evaluar
          </Badge>
        )}
        {repo.pr_evaluation_enabled && (
          <Badge kind="tone" value="brass">
            auto
          </Badge>
        )}
        {repo.private && (
          <Badge kind="tone" value="neutral">
            privado
          </Badge>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-[var(--taro-line)] pt-4">
        {repo.rule_count != null && (
          <Eyebrow>
            {repo.rule_count} regla{repo.rule_count !== 1 ? "s" : ""}
          </Eyebrow>
        )}
        {repo.language && (
          <Mono className="text-[11px] text-[var(--taro-ink-dim)]">
            {repo.language}
          </Mono>
        )}
      </div>
    </Card>
  );
}
