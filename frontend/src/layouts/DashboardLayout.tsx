import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  ScanSearch,
  FolderKanban,
  FileText,
  HelpCircle,
  ArrowRight,
  LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

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
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const displayName = user?.fullName || user?.email?.split('@')[0] || "Investigator";
  const userInitial = displayName.charAt(0).toUpperCase();
  const roleDisplay = user?.roles?.map(r => r.replace('ROLE_', '')).join(', ') || "Analyst";

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

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

          <div className="user-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
              <div className="user-avatar">
                {userInitial}
              </div>

              <div className="user-info">
                <strong>{displayName}</strong>
                <small>{roleDisplay}</small>
              </div>
            </div>

            <button
              onClick={handleLogout}
              className="icon-button"
              aria-label="Log Out"
              title="Log Out"
              style={{ color: 'var(--text-secondary)' }}
            >
              <LogOut size={16} />
            </button>
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

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button className="profile-button">
                <span className="user-avatar small">
                  {userInitial}
                </span>

                <span className="profile-name">
                  {displayName}
                </span>
              </button>

              <button
                onClick={handleLogout}
                className="icon-button"
                aria-label="Logout"
                title="Logout"
                style={{ marginLeft: '4px' }}
              >
                <LogOut size={16} strokeWidth={1.8} />
              </button>
            </div>
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