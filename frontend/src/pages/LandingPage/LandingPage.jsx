import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";

const API_URL = import.meta.env.VITE_API_URL || "";

const features = [
  {
    title: "Reglas en lenguaje natural",
    desc: "Define criterios de evaluación como texto libre. La IA los interpreta y los aplica sobre el código real del PR.",
  },
  {
    title: "Feedback automático en el PR",
    desc: "Los colaboradores reciben un comentario detallado con su puntuación y las reglas que han superado o no.",
  },
  {
    title: "Cross-check con dos modelos",
    desc: "Dos LLMs evalúan de forma independiente y votan en consenso para obtener el resultado más fiable.",
  },
  {
    title: "Control por repositorio",
    desc: "Configura umbrales de aprobación, número máximo de intentos y más, de forma independiente por tarea.",
  },
  {
    title: "Vista de colaboradores",
    desc: "Consulta el historial de contribuciones de cada colaborador a través de todos tus repositorios desde un único panel.",
  },
  {
    title: "Estado en tiempo real",
    desc: "El commit de GitHub cambia a pendiente mientras se evalúa y a verde o rojo al finalizar automáticamente.",
  },
];

function GitHubIcon({ size = 16 }) {
  return (
    <svg
      height={size}
      viewBox="0 0 16 16"
      width={size}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

export function LandingPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) navigate("/dashboard", { replace: true });
  }, [user, loading, navigate]);

  function handleLogin() {
    window.location.href = `${API_URL}/auth/login`;
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {/* Header */}
      <header
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
        className="sticky top-0 z-10 bg-[var(--color-bg)/90] backdrop-blur-sm"
      >
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-[var(--color-primary)]">
              <svg
                width="11"
                height="11"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
            </div>
            <span className="text-[13px] font-semibold text-[var(--color-text)]">
              CodeReview AI
            </span>
          </div>
          <button
            onClick={handleLogin}
            style={{ border: "1px solid rgba(255,255,255,0.15)" }}
            className="flex items-center gap-2 rounded-md bg-[#f5f5f5] px-3.5 py-1.5 text-[13px] font-medium text-[#111] transition-colors hover:bg-white"
          >
            <GitHubIcon size={14} />
            Acceder con GitHub
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-28 text-center">
        <p className="mb-5 text-[13px] text-[var(--color-text-muted)]">
          Plataforma de corrección automática · Trabajo de Fin de Grado
        </p>
        <h1 className="mx-auto max-w-2xl text-5xl font-bold leading-[1.1] tracking-tight text-[var(--color-text)] md:text-6xl">
          Evaluación de código con inteligencia artificial
        </h1>
        <p className="mx-auto mt-6 max-w-lg text-[15px] leading-relaxed text-[var(--color-text-muted)]">
          Define reglas de validación, conecta tus repositorios de GitHub y deja
          que la IA evalúe automáticamente los pull requests de tus colaboradores.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3">
          <button
            onClick={handleLogin}
            className="flex items-center gap-2.5 rounded-md bg-[var(--color-text)] px-5 py-2.5 text-[14px] font-semibold text-[var(--color-bg)] transition-opacity hover:opacity-90"
          >
            <GitHubIcon size={16} />
            Comenzar con GitHub
          </button>
          <p className="text-[12px] text-[var(--color-text-muted)]">
            Solo para dueños de repositorio · Los colaboradores interactúan a través de
            GitHub
          </p>
        </div>
      </section>

      {/* Features */}
      <section
        style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
        className="mx-auto w-full max-w-5xl px-6 py-16"
      >
        <p className="mb-10 text-center text-[13px] uppercase tracking-widest text-[var(--color-text-muted)]">
          Funcionalidades
        </p>
        <div className="grid grid-cols-1 gap-px bg-[rgba(255,255,255,0.07)] sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="bg-[var(--color-bg)] p-6">
              <h3 className="mb-2 text-[14px] font-semibold text-[var(--color-text)]">
                {f.title}
              </h3>
              <p className="text-[13px] leading-relaxed text-[var(--color-text-muted)]">
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
        className="py-5 text-center text-[12px] text-[var(--color-text-muted)]"
      >
        CodeReview AI · Trabajo de Fin de Grado
      </footer>
    </div>
  );
}
