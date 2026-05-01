import { useState, useEffect } from "react";
import { fetchRepoConfig, saveRepoConfig, fetchAppInfo } from "@/entities/repoConfig/api";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Spinner } from "@/shared/ui/Spinner";

function thresholdColor(pct) {
  if (pct < 40) return { track: "#ef4444", text: "text-red-400" };
  if (pct < 70) return { track: "#f59e0b", text: "text-amber-400" };
  if (pct < 90) return { track: "#6366f1", text: "text-indigo-400" };
  return { track: "#22c55e", text: "text-emerald-400" };
}

function ThresholdSlider({ value, onChange }) {
  const pct = Math.round(value * 100);
  const { track, text } = thresholdColor(pct);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--color-text)]">
          Umbral de aprobación
        </span>
        <span className={`text-lg font-bold tabular-nums ${text}`}>
          {pct}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={pct}
        onChange={(e) => onChange(parseInt(e.target.value, 10) / 100)}
        className="w-full h-2 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, ${track} ${pct}%, var(--color-border) ${pct}%)`,
          accentColor: track,
        }}
      />
      <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
        <span>0%</span>
        <span className="text-xs text-[var(--color-text-muted)]">
          Porcentaje mínimo de reglas superadas para aprobar el PR
        </span>
        <span>100%</span>
      </div>
    </div>
  );
}

function Toggle({ label, description, checked, onChange }) {
  return (
    <label className="flex items-start justify-between gap-4 cursor-pointer">
      <div>
        <p className="text-sm font-medium text-[var(--color-text)]">{label}</p>
        {description && (
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {description}
          </p>
        )}
      </div>
      <div
        onClick={() => onChange(!checked)}
        className={`relative flex-shrink-0 mt-0.5 w-10 h-5 rounded-full transition-colors duration-200 cursor-pointer ${
          checked ? "bg-indigo-600" : "bg-[var(--color-border)]"
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </div>
    </label>
  );
}

const DEFAULTS = {
  max_evaluations_per_pr: 3,
  approval_threshold: 0.8,
  enable_cross_check: true,
  pr_evaluation_enabled: true,
  max_chunks_per_rule: 5,
  llm_model: null,
  llm_primary_model: null,
  llm_secondary_model: null,
};

function ModelSelect({ label, description, value, onChange, models, defaultLabel }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-[var(--color-text)]">{label}</label>
      {description && (
        <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
      )}
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-indigo-500 appearance-none cursor-pointer"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 0.75rem center" }}
      >
        <option value="">{defaultLabel}</option>
        {models.map((m) => (
          <option key={m.id} value={m.id}>{m.display_name}</option>
        ))}
      </select>
    </div>
  );
}

export function RepoSettingsForm({ owner, repo }) {
  const [settings, setSettings] = useState(DEFAULTS);
  const [availableModels, setAvailableModels] = useState([]);
  const [defaultModels, setDefaultModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchRepoConfig(owner, repo),
      fetchAppInfo(),
    ])
      .then(([config, info]) => {
        setSettings({ ...DEFAULTS, ...config });
        const models = info.available_llm_models ?? [];
        setAvailableModels(models);
        const findName = (id) => models.find((m) => m.id === id)?.display_name ?? id;
        setDefaultModels({
          llm_model: findName(info.default_llm_model),
          llm_primary_model: findName(info.default_llm_primary_model),
          llm_secondary_model: findName(info.default_llm_secondary_model),
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [owner, repo]);

  function handleChange(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await saveRepoConfig(owner, repo, settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Máx. evaluaciones por PR"
          type="number"
          min={1}
          max={20}
          value={settings.max_evaluations_per_pr}
          onChange={(e) =>
            handleChange("max_evaluations_per_pr", parseInt(e.target.value, 10))
          }
          hint="Número máximo de veces que se puede evaluar un PR"
        />
        <Input
          label="Chunks por regla"
          type="number"
          min={1}
          max={20}
          value={settings.max_chunks_per_rule}
          onChange={(e) =>
            handleChange("max_chunks_per_rule", parseInt(e.target.value, 10))
          }
          hint="Número de fragmentos de código que se pasan al LLM por cada regla"
        />
      </div>

      <ThresholdSlider
        value={settings.approval_threshold}
        onChange={(v) => handleChange("approval_threshold", v)}
      />

      <div className="flex flex-col gap-4">
        <Toggle
          label="Evaluación automática de PRs"
          description="Si está desactivado, los pull requests de este repositorio no serán evaluados automáticamente"
          checked={settings.pr_evaluation_enabled}
          onChange={(v) => handleChange("pr_evaluation_enabled", v)}
        />
        <Toggle
          label="Cross-check (verificación dual)"
          description="Usa dos modelos LLM para validar cada regla y llegar a consenso"
          checked={settings.enable_cross_check}
          onChange={(v) => handleChange("enable_cross_check", v)}
        />
      </div>

      <div className="flex flex-col gap-3">
        <p className="text-sm font-semibold text-[var(--color-text)]">Modelos LLM</p>
        {settings.enable_cross_check ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ModelSelect
              label="Modelo principal"
              description="Utilizado como evaluador primario en el cross-check"
              value={settings.llm_primary_model}
              onChange={(v) => handleChange("llm_primary_model", v)}
              models={availableModels}
              defaultLabel={`Global (${defaultModels.llm_primary_model ?? "…"})`}
            />
            <ModelSelect
              label="Modelo secundario"
              description="Utilizado como evaluador secundario en el cross-check"
              value={settings.llm_secondary_model}
              onChange={(v) => handleChange("llm_secondary_model", v)}
              models={availableModels}
              defaultLabel={`Global (${defaultModels.llm_secondary_model ?? "…"})`}
            />
          </div>
        ) : (
          <ModelSelect
            label="Modelo LLM"
            description="Modelo utilizado para la evaluación de reglas"
            value={settings.llm_model}
            onChange={(v) => handleChange("llm_model", v)}
            models={availableModels}
            defaultLabel={`Global (${defaultModels.llm_model ?? "…"})`}
          />
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex justify-end">
        <Button
          type="submit"
          loading={saving}
          variant={saved ? "secondary" : "primary"}
        >
          {saved ? "Guardado" : "Guardar configuración"}
        </Button>
      </div>
    </form>
  );
}
