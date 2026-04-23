import { useState, useMemo, useRef, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { clsx } from "@/shared/lib/utils";

// ── Time ranges ───────────────────────────────────────────────────────────────

const RANGES = [
  { label: "Último día", value: "1d", hours: 24, groupBy: "hour" },
  { label: "7 días", value: "7d", hours: 168, groupBy: "day" },
  { label: "2 semanas", value: "14d", hours: 336, groupBy: "day" },
  { label: "Mes", value: "30d", hours: 720, groupBy: "day" },
];

// ── Data helpers ──────────────────────────────────────────────────────────────

function floorToHour(date) {
  const d = new Date(date);
  d.setMinutes(0, 0, 0);
  return d.toISOString();
}

function floorToDay(date) {
  return new Date(date).toISOString().slice(0, 10);
}

function formatHour(iso) {
  return new Date(iso).toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDay(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
  });
}

function buildBuckets(hours, groupBy) {
  const now = new Date();
  const buckets = [];
  if (groupBy === "hour") {
    for (let i = hours - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setHours(d.getHours() - i, 0, 0, 0);
      buckets.push({ key: d.toISOString(), label: formatHour(d) });
    }
  } else {
    for (let i = Math.floor(hours / 24) - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const day = d.toISOString().slice(0, 10);
      buckets.push({ key: day, label: formatDay(day) });
    }
  }
  return buckets;
}

function buildChartData(tasks, hours, groupBy) {
  const cutoff = new Date(Date.now() - hours * 3600 * 1000);
  const relevant = tasks.filter(
    (t) => t.created_at && new Date(t.created_at) >= cutoff,
  );
  const buckets = buildBuckets(hours, groupBy);
  const floor = groupBy === "hour" ? floorToHour : floorToDay;
  const counts = Object.fromEntries(
    buckets.map((b) => [b.key, { total: 0, completadas: 0, fallidas: 0 }]),
  );
  for (const t of relevant) {
    const key = floor(t.created_at);
    if (key in counts) {
      counts[key].total++;
      if (t.status === "completed") counts[key].completadas++;
      if (t.status === "failed") counts[key].fallidas++;
    }
  }
  return buckets.map((b) => ({ name: b.label, ...counts[b.key] }));
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs shadow-xl">
      <p className="font-semibold text-[var(--color-text)] mb-1.5">{label}</p>
      {payload.map((p) => (
        <p
          key={p.dataKey}
          className="flex items-center gap-2"
          style={{ color: p.color }}
        >
          <span
            className="h-1.5 w-3 rounded-full inline-block"
            style={{ background: p.color }}
          />
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
}

// ── Repo multi-select dropdown ────────────────────────────────────────────────

function RepoDropdown({ repoNames, selected, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const allSelected = selected.size === repoNames.length;
  const label =
    selected.size === 0
      ? "Ningún repositorio"
      : allSelected
        ? "Todos los repositorios"
        : selected.size === 1
          ? ([...selected][0].split("/")[1] ?? [...selected][0])
          : `${selected.size} repositorios`;

  function toggleAll() {
    onChange(allSelected ? new Set() : new Set(repoNames));
  }

  function toggleOne(name) {
    const next = new Set(selected);
    next.has(name) ? next.delete(name) : next.add(name);
    onChange(next);
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((p) => !p)}
        className={clsx(
          "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-colors",
          open
            ? "border-indigo-500 bg-[var(--color-surface-2)] text-[var(--color-text)]"
            : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text-muted)] hover:border-indigo-500/50 hover:text-[var(--color-text)]",
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-3.5 w-3.5 flex-shrink-0"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
        </svg>
        <span className="max-w-[180px] truncate">{label}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={clsx(
            "h-3.5 w-3.5 flex-shrink-0 transition-transform",
            open && "rotate-180",
          )}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-20 w-64 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-xl overflow-hidden">
          {/* Select all */}
          <button
            onClick={toggleAll}
            className="flex w-full items-center gap-2 px-3 py-2.5 text-xs font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-surface-2)] border-b border-[var(--color-border)] transition-colors"
          >
            <div
              className={clsx(
                "h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                allSelected
                  ? "bg-indigo-600 border-indigo-600"
                  : "border-[var(--color-border)]",
              )}
            >
              {allSelected && (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-2.5 w-2.5 text-white"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {!allSelected && selected.size > 0 && (
                <span className="h-1.5 w-1.5 rounded-sm bg-indigo-400 inline-block" />
              )}
            </div>
            Todos los repositorios
          </button>

          {/* Individual repos */}
          <div className="max-h-52 overflow-y-auto">
            {repoNames.map((name) => {
              const checked = selected.has(name);
              return (
                <button
                  key={name}
                  onClick={() => toggleOne(name)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-[var(--color-surface-2)] transition-colors"
                >
                  <div
                    className={clsx(
                      "h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                      checked
                        ? "bg-indigo-600 border-indigo-600"
                        : "border-[var(--color-border)]",
                    )}
                  >
                    {checked && (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-2.5 w-2.5 text-white"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                  <span className="truncate text-[var(--color-text)]">
                    {name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function ActivityChart({ tasks, repos = [] }) {
  const [range, setRange] = useState("7d");

  const repoNames = useMemo(() => {
    const fromTasks = [
      ...new Set(tasks.map((t) => t.repository_full_name).filter(Boolean)),
    ];
    if (repos.length > 0) {
      const fromRepos = repos.map((r) => r.full_name);
      return [...new Set([...fromRepos, ...fromTasks])];
    }
    return fromTasks;
  }, [tasks, repos]);

  const [selectedRepos, setSelectedRepos] = useState(() => new Set(repoNames));

  // Sync when repoNames resolves after mount
  const repoKey = repoNames.join(",");
  /* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */
  useEffect(() => {
    setSelectedRepos(new Set(repoNames));
  }, [repoKey])
  /* eslint-enable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */;

  const cfg = RANGES.find((r) => r.value === range);

  const filteredTasks = useMemo(
    () => tasks.filter((t) => selectedRepos.has(t.repository_full_name)),
    [tasks, selectedRepos],
  );

  const data = useMemo(
    () => buildChartData(filteredTasks, cfg.hours, cfg.groupBy),
    [filteredTasks, cfg],
  );

  const hasData = data.some((d) => d.total > 0);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
        <p className="text-sm font-semibold text-[var(--color-text)]">
          Actividad de evaluaciones
        </p>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Repo dropdown (only if >1 repo) */}
          {repoNames.length > 1 && (
            <RepoDropdown
              repoNames={repoNames}
              selected={selectedRepos}
              onChange={setSelectedRepos}
            />
          )}

          {/* Range selector */}
          <div className="flex rounded-lg border border-[var(--color-border)] overflow-hidden text-xs">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={clsx(
                  "px-3 py-1.5 transition-colors",
                  range === r.value
                    ? "bg-indigo-600 text-white"
                    : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface-2)]",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      {hasData ? (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart
            data={data}
            margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip />} />
            <Legend
              wrapperStyle={{
                fontSize: 12,
                paddingTop: 12,
                color: "var(--color-text-muted)",
              }}
            />
            <Line
              type="monotone"
              dataKey="total"
              name="Total"
              stroke="#8b8fa8"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="completadas"
              name="Completadas"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="fallidas"
              name="Fallidas"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-[220px] items-center justify-center">
          <p className="text-sm text-[var(--color-text-muted)]">
            Sin datos en este rango
          </p>
        </div>
      )}
    </div>
  );
}
