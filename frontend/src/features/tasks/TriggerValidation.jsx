import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { triggerValidation } from "@/entities/task/api";
import { fetchRepoConfig } from "@/entities/repoConfig/api";
import { Button } from "@/shared/ui/Button";

export function TriggerValidation({ owner, repo }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [crossCheck, setCrossCheck] = useState(true); // default until config loads
  const navigate = useNavigate();

  useEffect(() => {
    fetchRepoConfig(owner, repo)
      .then((cfg) => setCrossCheck(cfg.enable_cross_check))
      .catch(() => {});
  }, [owner, repo]);

  async function handleTrigger() {
    setLoading(true);
    setError(null);
    try {
      const task = await triggerValidation(owner, repo, crossCheck);
      navigate(`/tasks/${task.task_id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 items-end">
      <Button onClick={handleTrigger} loading={loading}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
            clipRule="evenodd"
          />
        </svg>
        Iniciar validación
      </Button>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
