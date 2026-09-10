import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { Button } from "@/shared/ui/Button";
import { BrandLockup } from "@/shared/ui/Brand";
import { Eyebrow, Body, SectionTitle, Mono } from "@/shared/ui/Typography";

const API_URL = import.meta.env.VITE_API_URL || "";

const RULE_EXAMPLES = [
  "Ninguna sentencia SQL fuera de la capa de repositorio",
  "Toda función pública debe llevar docstring con argumentos y retorno",
  "Las dependencias deben estar fijadas a versiones exactas",
  "Cada caso de uso depende de un puerto, nunca de un adaptador concreto",
];

const STEPS = [
  {
    n: "01",
    title: "Escribes la regla",
    desc: "En lenguaje natural, como se la explicarías a alguien que entra al equipo. Sin DSL ni configuración.",
  },
  {
    n: "02",
    title: "Taro lee el código",
    desc: "Indexa el repositorio, recupera los fragmentos que importan para esa regla y los cita en su respuesta.",
  },
  {
    n: "03",
    title: "El pull request recibe el veredicto",
    desc: "Correcto, parcial o incorrecto, con la explicación y los archivos en los que se apoya.",
  },
];

function GitHubIcon({ size = 16 }) {
  return (
    <svg height={size} viewBox="0 0 16 16" width={size} fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function TypedRule() {
  const [pos, setPos] = useState({ index: 0, count: 0 });

  useEffect(() => {
    const full = RULE_EXAMPLES[pos.index];
    const done = pos.count >= full.length;
    const delay = done ? 2600 : pos.count === 0 ? 260 : 28;

    const t = setTimeout(() => {
      setPos((p) =>
        p.count >= RULE_EXAMPLES[p.index].length
          ? { index: (p.index + 1) % RULE_EXAMPLES.length, count: 0 }
          : { index: p.index, count: p.count + 1 },
      );
    }, delay);

    return () => clearTimeout(t);
  }, [pos]);

  const shown = RULE_EXAMPLES[pos.index].slice(0, pos.count);

  return (
    <div className="mx-auto w-full max-w-2xl">
      <span className="mx-auto mb-8 block h-px w-full max-w-xl bg-[var(--taro-line)]" />

      <div className="flex h-[84px] items-center justify-center px-4">
        <Mono className="text-center text-[15px] leading-[1.5] whitespace-normal text-[var(--taro-ink)]">
          {shown}
          <span className="ml-0.5 inline-block h-[15px] w-[7px] translate-y-[2px] bg-[var(--taro-brass)]" />
        </Mono>
      </div>

      <div className="flex h-[32px] items-center justify-center">
        <span className="inline-flex items-center gap-2 rounded-[var(--taro-radius-control)] bg-[var(--taro-correct-bg)] px-[10px] py-[5px]">
          <Mono className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--taro-correct-ink)]">
            evaluada
          </Mono>
          <Mono className="text-[11px] text-[var(--taro-ink-dim)]">
            con los archivos citados
          </Mono>
        </span>
      </div>
    </div>
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
    <div className="flex min-h-screen flex-col bg-[var(--taro-bg)]">
      <header className="sticky top-0 z-10 border-b border-[var(--taro-line)] bg-[var(--taro-bg)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-4">
          <BrandLockup />
          <Button variant="github" size="sm" onClick={handleLogin}>
            <GitHubIcon size={14} />
            Acceder con GitHub
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <Eyebrow className="tracking-[0.2em]">
          Validación semántica de pull requests
        </Eyebrow>

        <h1 className="mx-auto mt-7 max-w-3xl font-[family-name:var(--taro-font-display)] text-[44px] font-semibold leading-[1.05] tracking-[-1.4px] text-[var(--taro-ink)] md:text-[64px]">
          Di la regla. <span className="text-[var(--taro-brass)]">Taro</span> la
          sostiene.
        </h1>

        <div className="mt-10 w-full">
          <TypedRule />
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" onClick={handleLogin}>
            <GitHubIcon size={16} />
            Comenzar con GitHub
          </Button>
          <a href="#como-funciona" className="hover:no-underline">
            <Button variant="secondary" size="lg">
              Cómo funciona
            </Button>
          </a>
        </div>

        <Body muted className="mt-6 max-w-md text-[13px]">
          Solo para dueños del repositorio. Los colaboradores interactúan desde
          GitHub, sin cuenta.
        </Body>
      </section>

      <div className="border-y border-[var(--taro-line)]">
        <div className="mx-auto grid max-w-5xl gap-6 px-6 py-6 md:grid-cols-3">
          {[
            "Reglas en lenguaje natural",
            "Dos modelos y un discriminador",
            "Cada veredicto cita sus archivos",
          ].map((t) => (
            <Mono
              key={t}
              className="text-center text-[12px] whitespace-normal text-[var(--taro-ink-dim)]"
            >
              {t}
            </Mono>
          ))}
        </div>
      </div>

      {/* Cómo funciona */}
      <section id="como-funciona" className="mx-auto w-full max-w-5xl px-6 py-24">
        <Eyebrow className="block text-center tracking-[0.2em]">
          Cómo una regla se convierte en evaluación
        </Eyebrow>

        <div className="mt-12 grid gap-px overflow-hidden rounded-[var(--taro-radius-panel)] border border-[var(--taro-line)] bg-[var(--taro-line)] md:grid-cols-3">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className="flex flex-col gap-3 bg-[var(--taro-surface)] px-7 py-8"
            >
              <Mono className="text-[11.5px] text-[var(--taro-brass)]">
                {s.n}
              </Mono>
              <SectionTitle className="text-[21px]">{s.title}</SectionTitle>
              <Body muted className="text-[13.5px]">
                {s.desc}
              </Body>
            </div>
          ))}
        </div>
      </section>

      {/* Cierre */}
      <section className="mx-auto w-full max-w-5xl px-6 pb-24">
        <div className="flex flex-col items-center gap-6 rounded-[var(--taro-radius-panel)] border border-[var(--taro-line)] bg-[var(--taro-surface)] px-8 py-14 text-center">
          <SectionTitle className="max-w-lg text-[28px]">
            Conecta un repositorio y escribe la primera regla.
          </SectionTitle>
          <Button size="lg" onClick={handleLogin}>
            <GitHubIcon size={16} />
            Comenzar con GitHub
          </Button>
        </div>
      </section>

      <footer className="border-t border-[var(--taro-line)] py-6 text-center">
        <Eyebrow className="normal-case tracking-[0.08em]">
          Taro · Trabajo de Fin de Grado
        </Eyebrow>
      </footer>
    </div>
  );
}
