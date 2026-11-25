import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  ScanSearch,
  History as HistoryIcon,
  FileText,
  Settings as SettingsIcon,
  LogOut,
  Shield,
  Activity,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navigation = [
  {
    label: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Upload & Ingest",
    path: "/upload",
    icon: Upload,
  },
  {
    label: "Analysis Workspace",
    path: "/analysis",
    icon: ScanSearch,
  },
  {
    label: "Analysis History",
    path: "/history",
    icon: HistoryIcon,
  },
  {
    label: "Evidence Reports",
    path: "/reports",
    icon: FileText,
  },
  {
    label: "Settings",
    path: "/settings",
    icon: SettingsIcon,
  },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const displayName = user?.fullName || user?.email?.split("@")[0] || "Investigator";
  const userInitial = displayName.charAt(0).toUpperCase();
  const roleDisplay = user?.roles?.map((r) => r.replace("ROLE_", "")).join(", ") || "Analyst";

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell" style={{ display: "flex", minHeight: "100vh", background: "var(--bg)", width: "100%" }}>
      {/* SIDEBAR */}
      <aside
        className="sidebar"
        style={{
          width: "250px",
          minWidth: "250px",
          maxWidth: "250px",
          height: "100vh",
          position: "sticky",
          top: 0,
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          padding: "20px 14px",
          flexShrink: 0,
          boxSizing: "border-box",
          zIndex: 40,
          overflowY: "auto",
        }}
      >
        {/* Brand */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "4px 8px 24px",
            borderBottom: "1px solid var(--border)",
            marginBottom: "18px",
          }}
        >
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "9px",
              background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
              color: "#ffffff",
              display: "grid",
              placeItems: "center",
              boxShadow: "0 2px 6px rgba(79, 70, 229, 0.3)",
            }}
          >
            <Shield size={20} strokeWidth={2.2} />
          </div>

          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, letterSpacing: "-0.3px", color: "var(--text)" }}>
              TruthLens
            </h2>
            <span style={{ fontSize: "11px", fontWeight: 500, color: "var(--text-muted)" }}>
              Authenticity Platform
            </span>
          </div>
        </div>

        {/* Navigation */}
        <div style={{ flex: 1 }}>
          <p
            style={{
              margin: "0 10px 8px",
              fontSize: "10px",
              fontWeight: 700,
              letterSpacing: "0.8px",
              color: "var(--text-muted)",
              textTransform: "uppercase",
            }}
          >
            Investigation
          </p>

          <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {navigation.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "8px",
                  fontSize: "13px",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "var(--primary)" : "var(--text-secondary)",
                  background: isActive ? "var(--primary-soft)" : "transparent",
                  textDecoration: "none",
                  transition: "all 0.15s ease",
                })}
              >
                <item.icon size={17} strokeWidth={1.9} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
          {/* AI Engine Status */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 12px",
              borderRadius: "8px",
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "var(--success)",
                boxShadow: "0 0 0 2px rgba(16, 185, 129, 0.2)",
              }}
            />
            <div style={{ overflow: "hidden" }}>
              <strong style={{ display: "block", fontSize: "11px", color: "var(--text)" }}>AI Engine v1.0.0</strong>
              <small style={{ display: "block", fontSize: "10px", color: "var(--text-muted)" }}>EfficientNet-B0 • 40 Demo Benchmarks</small>
            </div>
          </div>

          {/* User Profile Card */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 10px",
              borderRadius: "8px",
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  background: "var(--primary)",
                  color: "#ffffff",
                  fontSize: "12px",
                  fontWeight: 700,
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                }}
              >
                {userInitial}
              </div>

              <div style={{ overflow: "hidden" }}>
                <p style={{ margin: 0, fontSize: "12px", fontWeight: 650, color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {displayName}
                </p>
                <small style={{ fontSize: "10px", color: "var(--text-muted)" }}>{roleDisplay}</small>
              </div>
            </div>

            <button
              onClick={handleLogout}
              title="Sign Out"
              aria-label="Sign Out"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-secondary)",
                padding: "4px",
                cursor: "pointer",
                borderRadius: "4px",
                display: "grid",
                placeItems: "center",
              }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN VIEWPORT */}
      <div className="main-area" style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        {/* Top Header */}
        <header
          style={{
            height: "60px",
            background: "var(--surface)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 28px",
            position: "sticky",
            top: 0,
            zIndex: 30,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
            <span style={{ fontWeight: 600, color: "var(--text)" }}>TruthLens Platform</span>
            <span style={{ color: "var(--border)" }}>/</span>
            <span style={{ color: "var(--text-secondary)" }}>Digital Forensics</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "12px",
                color: "var(--text-secondary)",
                padding: "4px 10px",
                borderRadius: "6px",
                background: "var(--surface-soft)",
                border: "1px solid var(--border)",
              }}
            >
              <Activity size={13} style={{ color: "var(--success)" }} />
              <span>Production Pipeline</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1, padding: "28px", width: "100%", maxWidth: "100%", boxSizing: "border-box" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
