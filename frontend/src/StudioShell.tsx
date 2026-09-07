import type { ReactNode } from "react";
import { useAuth } from "./AuthGate";

type Props = {
  projectId: string;
  attemptId: string;
  children: ReactNode;
};

const navigation = [
  { index: "01", label: "Overview", href: "#overview" },
  { index: "02", label: "Develop", href: "#develop" },
  { index: "03", label: "Budget", href: "#budget-overview" },
  { index: "04", label: "Timeline", href: "#scene-title" },
];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

export default function StudioShell({
  projectId,
  attemptId,
  children,
}: Props) {
  const { user, signOut } = useAuth();
  const initials = user.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <div className="studio-shell">
      <aside className="studio-sidebar">
        <a className="shell-brand" href="#overview" aria-label="SceneFoundry studio">
          <BrandMark />
          <span>
            <strong>SceneFoundry</strong>
            <small>AI CINEMA STUDIO</small>
          </span>
        </a>

        <div className="sidebar-project">
          <span className="sidebar-label">ACTIVE PROJECT</span>
          <div className="project-identity">
            <span className="project-avatar">DC</span>
            <span>
              <strong>Demo Café</strong>
              <small>{projectId}</small>
            </span>
          </div>
        </div>

        <nav className="studio-navigation" aria-label="Studio navigation">
          <span className="sidebar-label">WORKSPACE</span>
          {navigation.map((item) => (
            <a key={item.href} className="nav-link" href={item.href}>
              <span className="nav-index">{item.index}</span>
              <span>{item.label}</span>
            </a>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="runtime-status">
            <span className="status-light" />
            <span>
              <strong>Production online</strong>
              <small>Google Cloud runtime</small>
            </span>
          </div>
          <p>Gemini direction · Veo motion · Private media</p>
        </div>
      </aside>

      <div className="shell-content">
        <header className="shell-topbar">
          <div className="breadcrumb">
            <span>Studio</span>
            <span>/</span>
            <strong>Director workspace</strong>
          </div>

          <div className="topbar-context">
            <span className="live-pill">
              <span className="status-light" />
              Live
            </span>
            <span className="attempt-pill">
              Attempt {attemptId.slice(0, 8)}
            </span>
            <button
              className="user-chip"
              type="button"
              onClick={signOut}
              title={`Signed in as ${user.email}. Click to sign out.`}
            >
              {user.picture_url ? (
                <img src={user.picture_url} alt="" referrerPolicy="no-referrer" />
              ) : (
                <span className="user-chip-avatar" aria-hidden="true">
                  {initials}
                </span>
              )}
              <span className="user-chip-copy">
                <strong>{user.name}</strong>
                <small>Sign out</small>
              </span>
            </button>
          </div>
        </header>

        {children}
      </div>
    </div>
  );
}