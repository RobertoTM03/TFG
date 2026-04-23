import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { getUserDisplayName } from "@/entities/user/model";
import { clsx } from "@/shared/lib/utils";

const navItems = [
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    to: "/repos",
    label: "Repositorios",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M3 3h7v7H3zM14 3h7v5M14 10h7v11H3v-7" />
        <path d="M14 3v7h4" />
      </svg>
    ),
  },
  {
    to: "/tasks",
    label: "Evaluaciones",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
        <rect x="9" y="3" width="6" height="4" rx="1" />
        <path d="M9 12h6M9 16h4" />
      </svg>
    ),
  },
  {
    to: "/contributors",
    label: "Colaboradores",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  const displayName = user ? getUserDisplayName(user) : "";

  return (
    <aside
      style={{ borderRight: "1px solid rgba(255,255,255,0.07)" }}
      className="flex h-full w-56 shrink-0 flex-col bg-[var(--color-surface)]"
    >
      {/* Logo / app name */}
      <div
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
        className="flex items-center gap-2.5 px-3 py-3"
      >
        <div className="flex h-5 w-5 items-center justify-center rounded bg-[var(--color-primary)]">
          <svg
            width="12"
            height="12"
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
        <span
          style={{ border: "1px solid rgba(255,255,255,0.12)" }}
          className="ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-muted)]"
        >
          TFG
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        <ul className="flex flex-col gap-px">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors",
                    isActive
                      ? "bg-[#1a1a1a] text-[var(--color-text)]"
                      : "text-[var(--color-text-muted)] hover:bg-[#111] hover:text-[var(--color-text)]",
                  )
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* User footer */}
      {user && (
        <div
          style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
          className="px-2 py-2"
        >
          <div className="flex items-center gap-2.5 rounded-md px-2.5 py-1.5">
            <img
              src={user.avatar_url}
              alt={displayName}
              className="h-6 w-6 rounded-full"
            />
            <span className="flex-1 truncate text-[13px] font-medium text-[var(--color-text)]">
              {displayName}
            </span>
            <button
              onClick={handleLogout}
              title="Cerrar sesión"
              className="text-[var(--color-text-muted)] transition-colors hover:text-red-400"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
