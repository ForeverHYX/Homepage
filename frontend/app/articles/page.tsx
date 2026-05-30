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

        <div className="article-grid">
          <div className="page-stack">


            {data.filter_tag ? (

              <div className="card home-glass article-card">
                <div className="home-glass-body" style={{ padding: "24px 28px" }}>
                  <span className="article-filter-label">
                    Filtered by tag: <strong>{data.filter_tag}</strong>
                  </span>
                  <Link href="/articles" className="article-card-link" style={{ marginTop: 0 }}>
                    Clear filter
                  </Link>
                </div>
              </div>
            ) : null}

            {data.articles.length ? (
              data.articles.map((article) => (
                <div className="card home-glass article-card" key={article.slug}>
                  <div className="home-glass-body" style={{ padding: "28px 32px" }}>
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
                </div>
              ))
            ) : (
              <p>No articles found.</p>
            )}
          </div>

          <aside className="sidebar" style={{ position: "sticky", top: 100 }}>
            <div className="card home-liquid-card home-news-card">
              <span className="home-liquid-warp" aria-hidden="true" />
              <div className="home-liquid-body">
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
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
