import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  ScanSearch,
  FolderKanban,
  FileText,
  HelpCircle,
  ChevronDown,
  ArrowRight,
} from "lucide-react";

const navigation = [
  {
    label: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Upload",
    path: "/upload",
    icon: Upload,
  },
  {
    label: "Analysis",
    path: "/analysis",
    icon: ScanSearch,
  },
  {
    label: "Cases",
    path: "/cases",
    icon: FolderKanban,
  },
  {
    label: "Reports",
    path: "/reports",
    icon: FileText,
  },
];

function DashboardLayout() {
  return (
    <div className="app-shell">
      {/* SIDEBAR */}
      <aside className="sidebar">
        {/* Brand */}
        <div className="brand">
          <div className="brand-mark">
            T
          </div>

          <div className="brand-copy">
            <h2>TruthLens</h2>
            <span>Evidence Intelligence</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="nav-section">
          <p className="nav-label">
            WORKSPACE
          </p>

          <nav
            className="main-navigation"
            aria-label="Main navigation"
          >
            {navigation.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  [
                    "nav-link",
                    isActive && "active",
                  ]
                    .filter(Boolean)
                    .join(" ")
                }
              >
               <span className="nav-icon">
  <item.icon size={17} strokeWidth={1.8} />
</span>

                <span className="nav-text">
                  {item.label}
                </span>

                <span className="nav-arrow">
  <ArrowRight size={13} />
</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Sidebar footer */}
        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />

            <div className="system-copy">
              <strong>System online</strong>
              <small>TruthLens API</small>
            </div>

            <span className="status-pulse" />
          </div>

          <div className="user-card">
            <div className="user-avatar">
              S
            </div>

            <div className="user-info">
              <strong>Sudheendra</strong>
              <small>Frontend Lead</small>
            </div>

            <span className="user-menu">
              ⋮
            </span>
          </div>
        </div>
      </aside>

      {/* MAIN APPLICATION */}
      <div className="main-area">
        {/* TOPBAR */}
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-label">
              TRUTHLENS
            </span>

            <div className="breadcrumb">
              <span>Workspace</span>
              <span className="breadcrumb-separator">
                /
              </span>
              <span className="breadcrumb-current">
                Investigation
              </span>
            </div>
          </div>

          <div className="topbar-actions">
          <button
  className="icon-button"
  aria-label="Help"
  title="Help"
>
  <HelpCircle size={16} strokeWidth={1.8} />
</button>

            <div className="topbar-divider" />

            <button className="profile-button">
              <span className="user-avatar small">
                S
              </span>

              <span className="profile-name">
                Sudheendra
              </span>

             <span className="profile-chevron">
  <ChevronDown size={14} />
</span>
            </button>
          </div>
        </header>

        {/* PAGE CONTENT */}
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;