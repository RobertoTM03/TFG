import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { Spinner } from "@/shared/ui/Spinner";
import { BrandLockup } from "@/shared/ui/Brand";
import { Eyebrow, Body } from "@/shared/ui/Typography";

export function AuthCallbackPage() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const token = params.get("token");
    if (!token) {
      navigate("/", { replace: true });
      return;
    }

    login(token).then(() => {
      navigate("/dashboard", { replace: true });
    });
  }, [params, login, navigate]);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <div className="flex flex-col justify-between gap-8 bg-[var(--taro-inset)] px-10 py-12 md:w-[380px]">
        <BrandLockup />
        <div>
          <Eyebrow className="block">Validación semántica</Eyebrow>
          <p className="mt-3 font-[family-name:var(--taro-font-display)] text-[28px] font-semibold leading-[1.15] tracking-[-0.6px] text-[var(--taro-ink)] [text-wrap:pretty]">
            Di la regla. Taro la sostiene.
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-5 bg-[var(--taro-bg)] px-10 py-12">
        <Spinner size="lg" />
        <Body muted>Iniciando sesión…</Body>
      </div>
    </div>
  );
}
