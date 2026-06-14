import type { Metadata } from "next";
import Link from "next/link";
import { CalendarIcon, UserIcon } from "@/components/icons";
import { getDailyPayload } from "@/lib/api";
import { DailyActions } from "@/app/daily/daily-actions";

type DailyPageProps = {
  searchParams: Promise<{
    keywords?: string;
    item_type?: string;
    paper_id?: string;
  }>;
};

export const metadata: Metadata = {
  title: "Daily",
  description: "Daily AI-curated papers and repositories for agentic computer architecture, co-design, simulators, and HPC systems.",
};

function dailyUrl(keywords: string[] = [], itemType = ""): string {
  const params = new URLSearchParams();
  if (keywords.length) params.set("keywords", keywords.join(","));
  if (itemType === "paper" || itemType === "repository") params.set("item_type", itemType);
  const query = params.toString();
  return query ? `/daily?${query}` : "/daily";
}

function keywordsUrl(currentKeywords: string[], toggle?: string, itemType = ""): string {
  let next: string[];
  if (!toggle) {
    next = currentKeywords;
  } else if (currentKeywords.includes(toggle)) {
    next = currentKeywords.filter((keyword) => keyword !== toggle);
  } else {
    next = [...currentKeywords, toggle];
  }
  return dailyUrl(next, itemType);
}

function typeUrl(itemType = ""): string {
  return dailyUrl([], itemType);
}

function paperAnchorId(id: string): string {
  return `paper-${id.replace(/[/:]/g, "-")}`;
}

function StarIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2.8l2.78 5.63 6.22.9-4.5 4.39 1.06 6.2L12 17l-5.56 2.92 1.06-6.2L3 9.33l6.22-.9L12 2.8z" />
    </svg>
  );
}

function ForkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <line x1="20" y1="4" x2="8.12" y2="15.88" />
      <line x1="14.47" y1="14.48" x2="20" y2="20" />
      <line x1="8.12" y1="8.12" x2="12" y2="12" />
    </svg>
  );
}

export default async function DailyPage({ searchParams }: DailyPageProps) {
  const { keywords, item_type: itemType, paper_id: paperId } = await searchParams;
  const data = await getDailyPayload(keywords || undefined, itemType || undefined);
  const activeKeywords = data.filter_keywords;
  const activeItemType = data.active_item_type;

  return (
    <div className="container">
      <div className="page-shell">
        <div className="article-grid daily-grid">
          <div className="page-stack">
            {activeKeywords.length > 0 ? (
              <div className="card home-glass article-card">
                <div className="home-glass-body" style={{ padding: "24px 28px" }}>
                  <span className="article-filter-label">
                    Filtered by:{" "}
                    {activeKeywords.map((keyword) => (
                      <Link
                        key={keyword}
                        href={keywordsUrl(activeKeywords, keyword, activeItemType)}
                        className="chip is-active"
                        style={{ cursor: "pointer", textDecoration: "none", marginRight: 6 }}
                      >
                        {keyword} &times;
                      </Link>
                    ))}
                  </span>
                  <Link href={typeUrl(activeItemType)} className="article-card-link" style={{ marginTop: 0 }}>
                    Clear all
                  </Link>
                </div>
              </div>
            ) : null}

            {data.items.length ? (
              data.items.map((item) => (
                <article
                  className={`card home-glass article-card daily-card${paperId === item.id ? " is-target" : ""}`}
                  key={item.id}
                  id={paperAnchorId(item.id)}
                >
                  <div className="home-glass-body" style={{ padding: "28px 32px" }}>
                    <h2 className="article-card-title">
                      <a href={item.paper_url || item.repository_url || "#"} target="_blank" rel="noreferrer">
                        {item.title}
                      </a>
                    </h2>
                    <div className="article-card-meta daily-card-meta daily-card-main-meta">
                      {item.display_authors.length ? (
                        <span className="daily-meta-authors">
                          <UserIcon /> {item.display_authors.join(", ")}
                        </span>
                      ) : null}
                      {data.run_date ? (
                        <span className="daily-meta-date">
                          <CalendarIcon /> {data.run_date}
                        </span>
                      ) : null}
                      <div className="chip-list daily-keyword-list">
                        {item.keywords.slice(0, 8).map((keyword) => (
                          <Link
                            key={`${item.id}-${keyword}`}
                            href={keywordsUrl(activeKeywords, keyword, activeItemType)}
                            className={`chip${activeKeywords.includes(keyword) ? " is-active" : ""}`}
                          >
                            {keyword}
                          </Link>
                        ))}
                      </div>
                    </div>
                    {item.item_type === "repository" && item.repository_url ? (
                      <a
                        className="github-repo-card daily-github-repo-card"
                        href={item.repository_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-repository-homepage={item.repository_homepage || undefined}
                      >
                        <div className="github-repo-top">
                          <strong>{item.repository_full_name || item.title}</strong>
                          {item.repository_language ? (
                            <span className="daily-github-language">
                              <span className="daily-github-language-dot" />
                              {item.repository_language}
                            </span>
                          ) : null}
                        </div>
                        {item.repository_description ? <div className="github-repo-desc">{item.repository_description}</div> : null}
                        <div className="github-repo-stats">
                          {item.repository_stars ? <span className="github-repo-stat"><StarIcon /> {item.display_repository_stars}</span> : null}
                          {item.repository_forks ? <span className="github-repo-stat"><ForkIcon /> {item.display_repository_forks}</span> : null}
                        </div>
                      </a>
                    ) : null}
                    <p className="article-card-summary daily-tldr">
                      {item.tldr}
                    </p>
                    <DailyActions item={item} feedbackConfig={data.feedback_config} runDate={data.run_date || "unknown"} />
                  </div>
                </article>
              ))
            ) : (
              <p>No daily recommendations found.</p>
            )}
          </div>

          <aside className="sidebar" style={{ position: "sticky", top: 100 }}>
            <div className="card home-liquid-card home-news-card">
              <span className="home-liquid-warp" aria-hidden="true" />
              <div className="home-liquid-body">
                <div className="daily-sidebar-heading">
                  <h3 className="sidebar-card-title">AI Keywords</h3>
                  <div className="daily-type-toggle" aria-label="Filter daily recommendation type">
                    <Link
                      href={typeUrl("")}
                      className={`daily-type-button daily-type-all${!activeItemType ? " is-active" : ""}`}
                      title="All"
                    >
                      All
                    </Link>
                    <Link
                      href={typeUrl("repository")}
                      className={`daily-type-button${activeItemType === "repository" ? " is-active" : ""}`}
                      title="Repositories"
                      aria-label="Repositories"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>
                    </Link>
                    <Link
                      href={typeUrl("paper")}
                      className={`daily-type-button${activeItemType === "paper" ? " is-active" : ""}`}
                      title="Papers"
                      aria-label="Papers"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" /></svg>
                    </Link>
                  </div>
                </div>
                <div className="chip-list daily-filter-chips">
                  {data.sorted_keywords.slice(0, 36).map(([keyword, count]) => {
                    const isActive = activeKeywords.includes(keyword);
                    return (
                      <Link
                        href={keywordsUrl(activeKeywords, keyword, activeItemType)}
                        className={`chip${isActive ? " is-active" : ""}`}
                        key={keyword}
                      >
                        {keyword} <span>({count})</span>
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
