import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login",
};

export default function LoginPage() {
  return (
    <div className="container" style={{ display: "flex", justifyContent: "center", paddingTop: "80px" }}>
      <div className="card" style={{ padding: "40px", borderRadius: "16px", width: "100%", maxWidth: "420px", border: "1px solid var(--border)" }}>
        <h1 style={{ margin: "0 0 8px", fontSize: "24px", color: "var(--heading)" }}>Welcome Back</h1>
        <p style={{ color: "var(--muted)", margin: "0 0 32px" }}>Sign in to manage your files</p>
        <form action="/api/login" method="POST">
          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: 500, color: "var(--text)" }}>Username</label>
            <input
              name="username"
              required
              autoFocus
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "16px",
                background: "var(--bg)",
                color: "var(--text)",
              }}
            />
          </div>
          <div style={{ marginBottom: "32px" }}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: 500, color: "var(--text)" }}>Password</label>
            <input
              type="password"
              name="password"
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "16px",
                background: "var(--bg)",
                color: "var(--text)",
              }}
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: "100%" }}>
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
