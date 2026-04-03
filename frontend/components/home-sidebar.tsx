/* eslint-disable @next/next/no-img-element */
"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import type { HomePayload } from "@/lib/types";
import { useActiveTheme } from "@/components/use-active-theme";

const LiquidGlass = dynamic(() => import("liquid-glass-react"), { ssr: false });

type HomeSidebarProps = {
  about: HomePayload["about"];
  avatarUrl: string;
  newsHtml: string;
  allNewsHtml: string;
};

export function HomeSidebar({
  about,
  avatarUrl,
  newsHtml,
  allNewsHtml,
}: HomeSidebarProps) {
  const theme = useActiveTheme();
  const [showAllNews, setShowAllNews] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(304);

  useEffect(() => {
    const updateWidth = () => {
      if (window.innerWidth < 900) {
        setSidebarWidth(Math.max(260, Math.min(window.innerWidth - 40, 560)));
      } else {
        setSidebarWidth(304);
      }
    };

    updateWidth();
    window.addEventListener("resize", updateWidth, { passive: true });
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  const glassProps = useMemo(
    () => ({
      cornerRadius: 32,
      padding: "0px",
      mode: "shader" as const,
      blurAmount: theme === "dark" ? 0.1 : 0.15,
      saturation: theme === "dark" ? 140 : 180,
      aberrationIntensity: theme === "dark" ? 1.4 : 1.8,
      displacementScale: theme === "dark" ? 56 : 62,
      overLight: theme !== "dark",
    }),
    [theme]
  );

  return (
    <>
      <aside className="sidebar home-sidebar home-react-sidebar">
        <div
          className="home-react-card-shell"
          style={{ width: sidebarWidth, minHeight: 432, position: "relative" }}
        >
          <LiquidGlass
            {...glassProps}
            className="home-profile-card"
            style={{ width: sidebarWidth, position: "absolute" }}
          >
            <div className="home-liquid-body">
              <img
                src={avatarUrl}
                className="avatar"
                alt="Avatar"
                onError={(event) => {
                  event.currentTarget.src =
                    "https://ui-avatars.com/api/?name=YH&background=3b82f6&color=fff&size=128";
                }}
              />
              <h1 className="profile-name">{about.name}</h1>
              <p className="profile-role">{about.role}</p>

              <div className="contact-links">
                <a href={about.email} className="contact-icon" title="Email">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" /></svg>
                </a>
                <a href={about.github} className="contact-icon" target="_blank" rel="noreferrer" title="GitHub">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" /><path d="M9 18c-4.51 2-5-2-7-2" /></svg>
                </a>
              </div>

              <div className="location">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></svg>{" "}
                <span>{about.location}</span>
              </div>
            </div>
          </LiquidGlass>
        </div>

        <div
          className="home-react-card-shell"
          style={{ width: sidebarWidth, minHeight: 278, position: "relative" }}
        >
          <LiquidGlass
            {...glassProps}
            className="home-news-card"
            style={{ width: sidebarWidth, position: "absolute" }}
          >
            <div className="home-liquid-body">
              <h3 className="news-title">
                <span>News</span>
                <button
                  type="button"
                  className="news-expand-btn"
                  title="View All"
                  aria-label="View all news"
                  onClick={() => setShowAllNews(true)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" /></svg>
                </button>
              </h3>
              <div dangerouslySetInnerHTML={{ __html: newsHtml }} />
            </div>
          </LiquidGlass>
        </div>
      </aside>

      {showAllNews ? (
        <div
          className="lightbox-overlay active"
          onClick={() => setShowAllNews(false)}
          style={{ display: "flex" }}
        >
          <div
            className="card lightbox-content news-modal-card"
            style={{
              padding: 40,
              maxWidth: 600,
              width: "90%",
              maxHeight: "80vh",
              overflowY: "auto",
              position: "relative",
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              onClick={() => setShowAllNews(false)}
              style={{
                position: "absolute",
                top: 20,
                right: 20,
                background: "none",
                border: "none",
                fontSize: 24,
                color: "var(--muted)",
                cursor: "pointer",
              }}
            >
              &times;
            </button>
            <h2
              style={{
                marginTop: 0,
                borderLeft: "5px solid var(--primary)",
                paddingLeft: 12,
              }}
            >
              All News
            </h2>
            <div dangerouslySetInnerHTML={{ __html: allNewsHtml }} />
          </div>
        </div>
      ) : null}
    </>
  );
}
