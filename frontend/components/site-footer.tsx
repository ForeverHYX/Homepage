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
      </div>
    </footer>
  );
}
