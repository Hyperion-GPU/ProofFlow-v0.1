import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/cases", label: "Cases" },
  { to: "/artifacts", label: "Artifacts" },
  { to: "/search", label: "Search" },
  { to: "/localproof", label: "LocalProof" },
  { to: "/agentguard", label: "AgentGuard" },
  { to: "/decisions", label: "Decisions" },
];

export function Layout() {
  return (
    <div className="app-frame">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">PF</span>
          <div>
            <strong>ProofFlow</strong>
            <span>Local MVP</span>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="workspace">
        <Outlet />
      </main>
    </div>
  );
}
