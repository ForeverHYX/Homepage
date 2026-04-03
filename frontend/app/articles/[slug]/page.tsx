import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CalendarIcon, ClockIcon, UserIcon } from "@/components/icons";
import { getArticleDetailPayload } from "@/lib/api";
import type { ArticleDetailPayload } from "@/lib/types";

type ArticleDetailPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateMetadata({
  params,
}: ArticleDetailPageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const article = await getArticleDetailPayload(slug);
    return {
      title: article.title,
    };
  } catch {
    return {
      title: "Article",
    };
  }
}

export default async function ArticleDetailPage({
  params,
}: ArticleDetailPageProps) {
  const { slug } = await params;
  let article: ArticleDetailPayload;

  try {
    article = await getArticleDetailPayload(slug);
  } catch {
    notFound();
  }

  return (
    <div className="container article-grid" style={{ marginTop: 40, marginBottom: 60 }}>
      <main className="card content-area" style={{ padding: 40, minWidth: 0 }}>
        <div style={{ marginBottom: 20 }}>
          <Link
            href="/articles"
            className="action-btn"
            style={{
              textDecoration: "none",
              paddingLeft: 0,
              color: "var(--text)",
              fontWeight: 500,
            }}
          >
            &larr; Back to Articles
          </Link>
        </div>

        <header style={{ marginBottom: 24 }}>
          <h1
            style={{
              fontSize: "2.5rem",
              fontWeight: 600,
              margin: "0 0 16px 0",
              borderLeft: "6px solid var(--primary)",
              paddingLeft: 16,
              lineHeight: 1.2,
              color: "var(--heading)",
            }}
          >
            {article.title}
          </h1>
          <div
            style={{
              display: "flex",
              gap: 24,
              color: "var(--muted)",
              fontSize: 15,
              paddingLeft: 22,
              marginBottom: 16,
              flexWrap: "wrap",
            }}
          >
            <span style={{ display: "flex", alignItems: "center" }}>
              <CalendarIcon /> {article.date_str}
            </span>
            <span style={{ display: "flex", alignItems: "center" }}>
              <UserIcon /> {article.author}
            </span>
            <span style={{ display: "flex", alignItems: "center" }}>
              <ClockIcon /> {article.word_count} words &middot; {article.read_time} min read
            </span>
            {article.tags.length ? (
              <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                {article.tags.map((tag) => (
                  <span
                    key={tag}
                    style={{
                      background: "var(--surface-highlight)",
                      color: "var(--text)",
                      fontSize: 11,
                      padding: "2px 6px",
                      borderRadius: 4,
                      border: "1px solid var(--border)",
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </header>

        <article
          className="prose"
          dangerouslySetInnerHTML={{ __html: article.html_body }}
        />
      </main>

      <aside>
        <div className="toc" style={{ position: "sticky", top: 100 }}>
          <p
            style={{
              fontWeight: 700,
              color: "var(--heading)",
              marginTop: 0,
              marginBottom: 12,
              fontSize: 14,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Contents
          </p>
          <div dangerouslySetInnerHTML={{ __html: article.toc_html }} />
        </div>
      </aside>
    </div>
  );
}
