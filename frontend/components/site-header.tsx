"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { HomeIcon, MoonIcon, SearchIcon, SunIcon } from "@/components/icons";
import type { SearchEntry } from "@/lib/types";
import { useActiveTheme } from "@/components/use-active-theme";

export function SiteHeader() {
  const pathname = usePathname();
  const theme = useActiveTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchIndex, setSearchIndex] = useState<SearchEntry[] | null>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);
  const searchBarRef = useRef<HTMLDivElement | null>(null);
  const searchTriggerRef = useRef<HTMLButtonElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const lightSheet = document.getElementById("hljs-light") as HTMLLinkElement | null;
    const darkSheet = document.getElementById("hljs-dark") as HTMLLinkElement | null;
    if (!lightSheet || !darkSheet) {
      return;
    }
    if (theme === "dark") {
      lightSheet.disabled = true;
      darkSheet.disabled = false;
    } else {
      darkSheet.disabled = true;
      lightSheet.disabled = false;
    }
  }, [theme]);

  useEffect(() => {
    if (searchOpen) {
      window.setTimeout(() => searchInputRef.current?.focus(), 100);
    }
    if (searchOpen && !searchIndex) {
      fetch("/api/search-index")
        .then((response) => response.json())
        .then((data: SearchEntry[]) => setSearchIndex(data))
        .catch(() => setSearchIndex([]));
    }
  }, [pathname, searchIndex, searchOpen]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        searchOpen &&
        searchBarRef.current &&
        searchTriggerRef.current &&
        !searchBarRef.current.contains(target) &&
        !searchTriggerRef.current.contains(target)
      ) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [searchOpen]);

  const hits = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized || !searchIndex) {
      return [];
    }
    return searchIndex.filter((item) => {
      const tags = item.tags ?? [];
      return (
        item.title.toLowerCase().includes(normalized) ||
        item.desc.toLowerCase().includes(normalized) ||
        tags.some((tag) => tag.toLowerCase().includes(normalized))
      );
    });
  }, [query, searchIndex]);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    document.documentElement.style.colorScheme = nextTheme;
    localStorage.setItem("theme", nextTheme);
  };

  return (
    <header className="site-header">
      <div
        className={`container nav${searchOpen ? " search-mode" : ""}`}
        ref={headerRef}
      >
        <Link
          href="/"
          className="brand"
          onClick={() => {
            setSearchOpen(false);
            setQuery("");
          }}
        >
          <HomeIcon />
          <span>Yixun Hong&apos;s Homepage</span>
        </Link>
        <div style={{ position: "relative", display: "flex", alignItems: "center", marginLeft: "auto" }}>
          <div
            id="navLinks"
            className="nav-links"
            style={{ display: "flex", gap: 20, fontWeight: 500, alignItems: "center" }}
          >
            <Link
              href="/"
              style={{ textDecoration: "none", color: "var(--text)" }}
              onClick={() => {
                setSearchOpen(false);
                setQuery("");
              }}
            >
              Home
            </Link>
            <Link
              href="/articles"
              style={{ textDecoration: "none", color: "var(--text)" }}
              onClick={() => {
                setSearchOpen(false);
                setQuery("");
              }}
            >
              Articles
            </Link>
            <Link
              href="/gallery"
              style={{ textDecoration: "none", color: "var(--text)" }}
              onClick={() => {
                setSearchOpen(false);
                setQuery("");
              }}
            >
              Gallery
            </Link>
            <a
              href="/uploads/transcript.pdf"
              target="_blank"
              rel="noreferrer"
              style={{ textDecoration: "none", color: "var(--text)" }}
            >
              Resume
            </a>
            <a href="/upload" style={{ textDecoration: "none", color: "var(--text)" }}>
              Upload
            </a>
          </div>

          <div
            className="nav-links"
            style={{ width: 1, height: 24, background: "var(--border)", margin: "0 12px" }}
          />

          <button
            id="searchTrigger"
            className="action-btn search-trigger"
            title="Search"
            ref={searchTriggerRef}
            onClick={() => setSearchOpen(true)}
          >
            <SearchIcon />
          </button>

          <div id="inlineSearchBar" className="search-bar-container" ref={searchBarRef}>
            <SearchIcon
              width={18}
              height={18}
              style={{ color: "var(--muted)", marginLeft: 12, marginRight: 8, flexShrink: 0 }}
            />
            <input
              ref={searchInputRef}
              type="text"
              id="inlineSearchInput"
              placeholder="Search..."
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 15,
                width: "100%",
                color: "var(--text)",
                height: 40,
              }}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoComplete="off"
            />
            <button
              onClick={() => {
                setSearchOpen(false);
                setQuery("");
              }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", padding: "0 12px" }}
            >
              &times;
            </button>
            <div
              id="searchDropdown"
              className={`search-dropdown${query.trim() ? " has-results" : ""}`}
            >
              <div id="inlineSearchResults" style={{ padding: "8px 0" }}>
                {query.trim() ? (
                  hits.length ? (
                    hits.map((hit) => (
                      <Link href={hit.url} key={`${hit.type}-${hit.url}`} onClick={() => setSearchOpen(false)}>
                        <div className="search-result-title">
                          <span className="search-result-chip">{hit.type}</span>
                          {hit.title}
                        </div>
                      </Link>
                    ))
                  ) : (
                    <div style={{ padding: 12, textAlign: "center", color: "var(--muted)" }}>
                      No results found.
                    </div>
                  )
                ) : null}
              </div>
            </div>
          </div>

          <button
            id="themeToggle"
            className="action-btn"
            title="Toggle Theme"
            style={{ marginLeft: 8 }}
            onClick={toggleTheme}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}
