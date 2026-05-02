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
