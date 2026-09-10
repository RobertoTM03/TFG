/**
 * Los tres vocabularios de estado de la app se mantienen separados a propósito:
 * "task" (TASK_STATUS), "verdict" (evaluation.verdict) y "error" (parseTaskError).
 * "tone" no es un estado, es el cromo neutro y de marca.
 *
 * Los valores son nombres de token declarados en shared/styles/taro.css.
 */

const NEUTRAL = {
  label: null,
  ink: "--taro-ink-dim",
  ground: "--taro-raised",
  accent: "--taro-line-strong",
  line: "--taro-line-strong",
};

const CORRECT = {
  ink: "--taro-correct-ink",
  ground: "--taro-correct-bg",
  accent: "--taro-correct",
  line: "--taro-correct-line",
};

const PARTIAL = {
  ink: "--taro-partial-ink",
  ground: "--taro-partial-bg",
  accent: "--taro-partial",
  line: "--taro-partial-line",
};

const INCORRECT = {
  ink: "--taro-incorrect-ink",
  ground: "--taro-incorrect-bg",
  accent: "--taro-incorrect",
  line: "--taro-incorrect-line",
};

const BRASS = {
  ink: "--taro-brass",
  ground: "--taro-inset",
  accent: "--taro-line-brass",
  line: "--taro-line-brass",
};

const MAPS = {
  task: {
    pending: { ...NEUTRAL, label: "Pendiente" },
    running: { ...PARTIAL, label: "Ejecutando" },
    completed: { ...CORRECT, label: "Completado" },
    failed: { ...INCORRECT, label: "Fallido" },
  },

  verdict: {
    pass: { ...CORRECT, label: "Correcto" },
    partial: { ...PARTIAL, label: "Parcial" },
    fail: { ...INCORRECT, label: "Incorrecto" },
  },

  // El mensaje legible lo da parseTaskError, no este mapa.
  error: {
    LLM_UNAVAILABLE: { ...INCORRECT, label: null },
    EMBEDDING_UNAVAILABLE: { ...INCORRECT, label: null },
    UNEXPECTED_ERROR: { ...INCORRECT, label: null },
  },

  tone: {
    neutral: NEUTRAL,
    brass: { ...BRASS, label: null },
    correct: { ...CORRECT, label: null },
    partial: { ...PARTIAL, label: null },
    incorrect: { ...INCORRECT, label: null },

    // Alias transitorios del prop `color` anterior a Taro. Eliminar con el último uso.
    success: { ...CORRECT, label: null },
    danger: { ...INCORRECT, label: null },
    warning: { ...PARTIAL, label: null },
    primary: { ...BRASS, label: null },
    muted: NEUTRAL,
  },
};

export function token(name) {
  return `var(${name})`;
}

export function statusStyle(kind, value) {
  return MAPS[kind]?.[value] ?? NEUTRAL;
}

export function statusCss(kind, value) {
  const s = statusStyle(kind, value);
  return {
    color: token(s.ink),
    background: token(s.ground),
    borderColor: token(s.line),
    accentColor: token(s.accent),
  };
}

export function statusLabel(kind, value) {
  return statusStyle(kind, value).label ?? value ?? "—";
}
