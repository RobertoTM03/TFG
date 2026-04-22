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
    const verdict = v.cross_check?.primary_verdict ?? v.evaluation?.verdict;
    const confidence =
      v.cross_check?.primary_confidence ?? v.evaluation?.confidence ?? 0;
    if (verdict === "pass") return confidence;
    if (verdict === "partial") return confidence * 0.5;
    return 0;
  });
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

export function verdictCounts(validations = []) {
  return validations.reduce(
    (acc, v) => {
      const verdict =
        v.cross_check?.primary_verdict ?? v.evaluation?.verdict ?? "unknown";
      acc[verdict] = (acc[verdict] ?? 0) + 1;
      return acc;
    },
    { pass: 0, fail: 0, partial: 0 },
  );
}
