import type { Metadata } from "next";
import { HomeLegacyEffects } from "@/components/home-legacy-effects";
import { HomeSidebar } from "@/components/home-sidebar";
import { getHomePayload } from "@/lib/api";

export const metadata: Metadata = {
  title: "Home",
};

export default async function HomePage() {
  const home = await getHomePayload();

  return (
    <div className="container main-grid home-layout">
      <div className="home-lightfield" aria-hidden="true" />
      <HomeLegacyEffects />
      <HomeSidebar
        about={home.about}
        avatarUrl={home.avatar_url}
        newsHtml={home.news_html}
        allNewsHtml={home.all_news_html}
      />
      <main className="card home-content">
        <div className="home-glass-body">
          {home.sections.map((section, index) => (
            <section className="cv-section" key={`${section.title}-${index}`}>
              {section.title ? (
                <h2
                  className="section-title"
                  style={{ borderLeftColor: section.accent_color }}
                >
                  {section.title}
                </h2>
              ) : null}
              <div
                className="prose"
                dangerouslySetInnerHTML={{ __html: section.body_html }}
              />
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
