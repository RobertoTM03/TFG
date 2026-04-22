import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { Spinner } from "@/shared/ui/Spinner";

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
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-[var(--color-bg)]">
      <Spinner size="lg" />
      <p className="text-sm text-[var(--color-text-muted)]">
        Iniciando sesión…
      </p>
    </div>
  );
}
