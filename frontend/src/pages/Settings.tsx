import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  User,
  Shield,
  Server,
  Key,
  CheckCircle2,
  LogOut,
  Cpu,
  Laptop,
  Volume2,
} from "lucide-react";

export function Settings() {
  const { user, logout } = useAuth();
  const [copiedToken, setCopiedToken] = useState(false);

  const displayName = user?.fullName || user?.email?.split("@")[0] || "Investigator";
  const email = user?.email || "analyst@truthlens.com";
  const roles = user?.roles?.map((r) => r.replace("ROLE_", "")).join(", ") || "USER";

  const handleCopyToken = () => {
    const token = localStorage.getItem("truthlens_auth_token") || "";
    if (token) {
      navigator.clipboard.writeText(token);
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    }
  };

  return (
    <div className="settings-page" style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.2px", color: "var(--primary)", textTransform: "uppercase" }}>
          Configuration
        </span>
        <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "4px 0 6px", color: "var(--text)" }}>
          Settings & Preferences
        </h2>
        <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)" }}>
          Manage your account profile, inspection engine connections, and session preferences.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Profile Card */}
        <section
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "24px",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "18px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "var(--primary-soft)",
                color: "var(--primary)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <User size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>User Profile</h3>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>Your authenticated account information</p>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "16px",
              padding: "16px",
              background: "var(--surface-soft)",
              borderRadius: "10px",
              border: "1px solid var(--border)",
            }}
          >
            <div>
              <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>Full Name</span>
              <p style={{ margin: "4px 0 0", fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>{displayName}</p>
            </div>
            <div>
              <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>Email Address</span>
              <p style={{ margin: "4px 0 0", fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>{email}</p>
            </div>
            <div>
              <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>Assigned Role</span>
              <div style={{ marginTop: "4px" }}>
                <span
                  style={{
                    display: "inline-block",
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: "var(--primary-soft)",
                    color: "var(--primary)",
                  }}
                >
                  {roles}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* AI Engine & Backend Connectivity Card */}
        <section
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "24px",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "18px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "var(--success-soft)",
                color: "var(--success)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <Cpu size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>Connected Inspection Services</h3>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>Active AI engines and backend gateway endpoints</p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {/* Service 1 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 16px",
                background: "var(--surface-soft)",
                borderRadius: "10px",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Server size={18} style={{ color: "var(--primary)" }} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>FastAPI Vision Microservice</h4>
                  <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>http://localhost:8001</small>
                </div>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 650,
                  color: "var(--success)",
                }}
              >
                <CheckCircle2 size={14} />
                Online (Port 8001)
              </span>
            </div>

            {/* Service 2 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 16px",
                background: "var(--surface-soft)",
                borderRadius: "10px",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Laptop size={18} style={{ color: "var(--primary)" }} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>Spring Boot Backend Gateway</h4>
                  <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>http://localhost:8080 (REST / Flyway / PostgreSQL)</small>
                </div>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 650,
                  color: "var(--success)",
                }}
              >
                <CheckCircle2 size={14} />
                Connected (Port 8080)
              </span>
            </div>

            {/* Image Model Card */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 16px",
                background: "var(--surface-soft)",
                borderRadius: "10px",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Shield size={18} style={{ color: "#8b5cf6" }} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>PyTorch EfficientNet-B0 Image Model</h4>
                  <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>deepfake_detection_efficientnet_b0.pt (v1.0.0 &bull; Accuracy: 83.63%)</small>
                </div>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 650,
                  color: "var(--primary)",
                }}
              >
                Production Checkpoint
              </span>
            </div>

            {/* Audio Forensics Engine Card */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 16px",
                background: "var(--surface-soft)",
                borderRadius: "10px",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Volume2 size={18} style={{ color: "#f59e0b" }} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>Audio Authenticity & Voice Forensics</h4>
                  <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Spectral centroid, phase discontinuity & synthetic voice detection</small>
                </div>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 650,
                  color: "var(--success)",
                }}
              >
                <CheckCircle2 size={14} />
                Enabled
              </span>
            </div>
          </div>
        </section>

        {/* Security & Session Card */}
        <section
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "24px",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "18px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "var(--warning-soft)",
                color: "var(--warning)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <Key size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>Authentication & Session</h3>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>JWT credentials and active session control</p>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "14px" }}>
            <div>
              <p style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>Active Bearer Session Token</p>
              <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Stored securely in local storage for API requests</small>
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={handleCopyToken}
                style={{
                  padding: "8px 14px",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--surface-soft)",
                  color: "var(--text)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {copiedToken ? "Copied!" : "Copy JWT Token"}
              </button>

              <button
                onClick={() => logout()}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 14px",
                  borderRadius: "8px",
                  border: "1px solid #fecaca",
                  background: "var(--danger-soft)",
                  color: "var(--danger)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Settings;
