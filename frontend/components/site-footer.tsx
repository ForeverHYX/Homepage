export function SiteFooter() {
  return (
    <footer>
      <div className="container">
        &copy; {new Date().getFullYear()} Yixun Hong. Powered by{" "}
        <a
          href="https://github.com/ForeverHYX/Homepage"
          style={{ color: "inherit", textDecoration: "underline" }}
        >
          Yixun&apos;s Homepage
        </a>
        .
        <div style={{ marginTop: "10px" }}>
          <a
            href="https://beian.miit.gov.cn/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--muted)", textDecoration: "none", fontSize: "13px" }}
          >
            浙ICP备2023041507号-1
          </a>
        </div>
      </div>
    </footer>
  );
}
