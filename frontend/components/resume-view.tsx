import Link from "next/link";

export function ResumeView() {
  return (
    <div className="container">
      <div className="page-shell">
        <section className="cv-section">
          <div className="card home-liquid-card">
            <span className="home-liquid-warp" aria-hidden="true" />
            <div className="home-liquid-body" style={{ padding: 40 }}>
              <div className="card home-liquid-card" style={{ marginBottom: 24 }}>
                <span className="home-liquid-warp" aria-hidden="true" />
                <div className="home-liquid-body" style={{ padding: "28px 32px" }}>
                  <div style={{ marginBottom: 20 }}>
                    <Link
                      href="/"
                      className="action-btn"
                      style={{
                        textDecoration: "none",
                        paddingLeft: 0,
                        color: "var(--text)",
                        fontWeight: 500,
                      }}
                    >
                      &larr; Back to Home
                    </Link>
                  </div>

                  <h2
                    style={{
                      fontSize: "2.5rem",
                      fontWeight: 600,
                      margin: "0 0 12px 0",
                      lineHeight: 1.2,
                      color: "var(--heading)",
                    }}
                  >
                    Resume
                  </h2>
                  <p
                    style={{
                      color: "var(--muted)",
                      fontSize: 15,
                      margin: "0 0 8px 0",
                      lineHeight: 1.6,
                    }}
                  >
                    Yixun Hong &middot; Undergraduate at Zhejiang University
                  </p>
                </div>
              </div>

              <div
                className="resume-pdf-wrapper"
                style={{
                  borderRadius: 16,
                  overflow: "hidden",
                  boxShadow: "0 12px 40px rgba(15, 23, 42, 0.18)",
                  background: "var(--glass-lo-bg)",
                  backdropFilter: "blur(18px) saturate(165%)",
                  WebkitBackdropFilter: "blur(18px) saturate(165%)",
                  border: "1px solid var(--glass-hi-border)",
                }}
              >
                <iframe
                  src="/uploads/transcript.pdf"
                  title="Resume PDF"
                  className="resume-pdf-iframe"
                  style={{
                    width: "100%",
                    height: "min(80vh, 1000px)",
                    border: "none",
                    display: "block",
                  }}
                />
              </div>

              <div
                style={{
                  marginTop: 16,
                  textAlign: "center",
                  color: "var(--muted)",
                  fontSize: 14,
                }}
              >
                <a
                  href="/uploads/transcript.pdf"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="link-styled"
                >
                  Open PDF in new tab
                </a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
