export const TASK_ERROR_CODE = {
  LLM_UNAVAILABLE: "LLM_UNAVAILABLE",
  EMBEDDING_UNAVAILABLE: "EMBEDDING_UNAVAILABLE",
  UNEXPECTED_ERROR: "UNEXPECTED_ERROR",
};

const ERROR_TITLES = {
  [TASK_ERROR_CODE.LLM_UNAVAILABLE]: "Servicio de IA no disponible",
  [TASK_ERROR_CODE.EMBEDDING_UNAVAILABLE]: "Servicio de búsqueda no disponible",
  [TASK_ERROR_CODE.UNEXPECTED_ERROR]: "Error inesperado",
};

/**
 * Parses task.error — may be a JSON string (new format) or plain string (legacy).
 * Returns { code, message, technical, title }.
 */
export function parseTaskError(raw) {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.code && parsed.message) {
      return {
        code: parsed.code,
        message: parsed.message,
        technical: parsed.technical ?? null,
        title: ERROR_TITLES[parsed.code] ?? "Error en la evaluación",
      };
    }
  } catch {
    // legacy plain string
  }
  return {
    code: null,
    message: raw,
    technical: null,
    title: "Error en la evaluación",
  };
}

export const TASK_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
};

export function isTerminal(status) {
  return status === TASK_STATUS.COMPLETED || status === TASK_STATUS.FAILED;
}

export function computeOverallScore(validations = []) {
  if (!validations.length) return null;
  const scores = validations.map((v) => {
    const verdict = v.evaluation?.verdict;
    if (verdict === "pass") return 1;
    if (verdict === "partial") return 0.5;
    return 0;
  });
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

export function verdictCounts(validations = []) {
  return validations.reduce(
    (acc, v) => {
      const verdict = v.evaluation?.verdict ?? "unknown";
      acc[verdict] = (acc[verdict] ?? 0) + 1;
      return acc;
    },
    { pass: 0, fail: 0, partial: 0 },
  );
}
