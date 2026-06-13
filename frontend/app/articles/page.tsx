import type { Metadata } from "next";
import Link from "next/link";
import { CalendarIcon, UserIcon } from "@/components/icons";
import { getArticlesPayload } from "@/lib/api";

type ArticlesPageProps = {
  searchParams: Promise<{
    tags?: string;
  }>;
};

export const metadata: Metadata = {
  title: "Articles",
  description: "Articles and blog posts by Yixun Hong on Computer Architecture, GPU simulation, High-Performance Computing, and more.",
};

function tagsUrl(currentTags: string[], toggle?: string): string {
  let next: string[];
  if (!toggle) {
    next = currentTags;
  } else if (currentTags.includes(toggle)) {
    next = currentTags.filter((t) => t !== toggle);
  } else {
    next = [...currentTags, toggle];
  }
  if (next.length === 0) return "/articles";
  return `/articles?tags=${encodeURIComponent(next.join(","))}`;
}

export default async function ArticlesPage({ searchParams }: ArticlesPageProps) {
  const { tags } = await searchParams;
  const tagParam = tags || undefined;
  const data = await getArticlesPayload(tagParam);
  const activeTags = data.filter_tags;

  return (
    <div className="container">
      <div className="page-shell">

        <div className="article-grid">
          <div className="page-stack">


            {activeTags.length > 0 ? (

              <div className="card home-glass article-card">
                <div className="home-glass-body" style={{ padding: "24px 28px" }}>
                  <span className="article-filter-label">
                    Filtered by:{" "}
                    {activeTags.map((t) => (
                      <Link
                        key={t}
                        href={tagsUrl(activeTags, t)}
                        className="chip is-active"
                        style={{ cursor: "pointer", textDecoration: "none", marginRight: 6 }}
                      >
                        {t} &times;
                      </Link>
                    ))}
                  </span>
                  <Link href="/articles" className="article-card-link" style={{ marginTop: 0 }}>
                    Clear all
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
                        {article.tags.map((tagItem) => {
                          const isActive = activeTags.includes(tagItem);
                          return isActive ? (
                            <Link
                              key={`${article.slug}-${tagItem}`}
                              href={tagsUrl(activeTags, tagItem)}
                              className="chip is-active"
                              style={{ cursor: "pointer", textDecoration: "none" }}
                            >
                              {tagItem} &times;
                            </Link>
                          ) : (
                            <Link
                              key={`${article.slug}-${tagItem}`}
                              href={tagsUrl(activeTags, tagItem)}
                              className="chip"
                              style={{ cursor: "pointer", textDecoration: "none" }}
                            >
                              {tagItem}
                            </Link>
                          );
                        })}
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
                    className={`chip${activeTags.length === 0 ? " is-active" : ""}`}
                  >
                    All
                  </Link>
                  {data.sorted_tags.map(([tagName, count]) => {
                    const isActive = activeTags.includes(tagName);
                    return (
                      <Link
                        href={tagsUrl(activeTags, tagName)}
                        className={`chip${isActive ? " is-active" : ""}`}
                        key={tagName}
                      >
                        {tagName} <span>({count})</span>
                        {isActive ? " \u00d7" : ""}
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
