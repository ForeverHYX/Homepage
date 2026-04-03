import type { Metadata } from "next";
import Link from "next/link";
import { CalendarIcon, UserIcon } from "@/components/icons";
import { getArticlesPayload } from "@/lib/api";

type ArticlesPageProps = {
  searchParams: Promise<{
    tag?: string;
  }>;
};

export const metadata: Metadata = {
  title: "Articles",
};

export default async function ArticlesPage({ searchParams }: ArticlesPageProps) {
  const { tag } = await searchParams;
  const data = await getArticlesPayload(tag);

  return (
    <div className="container">
      <div className="page-shell">
        <div>
          <h1
            className="section-title"
            style={{
              borderLeftColor: "var(--primary)",
              marginBottom: 24,
              fontSize: "3rem",
              paddingBottom: 10,
            }}
          >
            Articles
          </h1>
          <p className="page-lead">Thoughts, tutorials, and updates.</p>
        </div>

        <div className="article-grid">
          <div className="page-stack">
            {data.filter_tag ? (
              <div className="card article-filter-bar">
                <span className="article-filter-label">
                  Filtered by tag: <strong>{data.filter_tag}</strong>
                </span>
                <Link href="/articles" className="article-card-link" style={{ marginTop: 0 }}>
                  Clear filter
                </Link>
              </div>
            ) : null}

            {data.articles.length ? (
              data.articles.map((article) => (
                <div className="card article-card" key={article.slug}>
                  <h2 className="article-card-title">
                    <Link href={`/articles/${article.slug}`}>{article.title}</Link>
                  </h2>
                  <div className="article-card-meta">
                    <span>
                      <CalendarIcon /> {article.date}
                    </span>
                    <span>
                      <UserIcon /> {article.author}
                    </span>
                    <div className="chip-list">
                      {article.tags.map((tagItem) => (
                        <span className="chip" key={`${article.slug}-${tagItem}`}>
                          {tagItem}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="article-card-summary">{article.summary}</p>
                  <Link href={`/articles/${article.slug}`} className="article-card-link">
                    Read more &rarr;
                  </Link>
                </div>
              ))
            ) : (
              <p>No articles found.</p>
            )}
          </div>

          <aside className="sidebar" style={{ position: "sticky", top: 100 }}>
            <div className="card sidebar-card">
              <h3 className="sidebar-card-title">Tags</h3>
              <div className="chip-list">
                <Link
                  href="/articles"
                  className={`chip${!data.filter_tag ? " is-active" : ""}`}
                >
                  All
                </Link>
                {data.sorted_tags.map(([tagName, count]) => (
                  <Link
                    href={`/articles?tag=${encodeURIComponent(tagName)}`}
                    className={`chip${data.filter_tag === tagName ? " is-active" : ""}`}
                    key={tagName}
                  >
                    {tagName} <span>({count})</span>
                  </Link>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
