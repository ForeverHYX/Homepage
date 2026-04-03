"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  HomeIcon,
  MenuIcon,
  MoonIcon,
  SearchIcon,
  SunIcon,
  XIcon,
} from "@/components/icons";
import type { SearchEntry } from "@/lib/types";
import { useActiveTheme } from "@/components/use-active-theme";

export function SiteHeader() {
  const pathname = usePathname();
  const theme = useActiveTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchIndex, setSearchIndex] = useState<SearchEntry[] | null>(null);
  const navClusterRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const closeSearch = () => {
    setSearchOpen(false);
    setQuery("");
  };

  const resetNavigationState = () => {
    closeSearch();
    setMobileMenuOpen(false);
  };

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
  }, [searchIndex, searchOpen]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (navClusterRef.current && !navClusterRef.current.contains(target)) {
        if (searchOpen) {
          setSearchOpen(false);
          setQuery("");
        }
        if (mobileMenuOpen) {
          setMobileMenuOpen(false);
        }
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [mobileMenuOpen, searchOpen]);

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

  const navItems = [
    {
      href: "/",
      label: "Home",
      active: pathname === "/",
      external: false,
    },
    {
      href: "/articles",
      label: "Articles",
      active: pathname === "/articles" || pathname.startsWith("/articles/"),
      external: false,
    },
    {
      href: "/gallery",
      label: "Gallery",
      active: pathname === "/gallery",
      external: false,
    },
    {
      href: "/uploads/transcript.pdf",
      label: "Resume",
      active: false,
      external: true,
    },
    {
      href: "/upload",
      label: "Upload",
      active: pathname === "/upload",
      external: false,
    },
  ];

  return (
    <header className="site-header">
      <div className="container nav-shell">
        <div className="nav-cluster" ref={navClusterRef}>
          <div className={`nav-island home-liquid-card${searchOpen ? " search-mode" : ""}`}>
            <span className="home-liquid-warp nav-island-warp" aria-hidden="true" />
            <div className="nav-island-body">
              <Link href="/" className="brand nav-brand" onClick={resetNavigationState}>
                <HomeIcon className="nav-brand-icon" />
                <span className="nav-brand-label nav-brand-label-full">
                  Yixun Hong&apos;s Homepage
                </span>
                <span className="nav-brand-label nav-brand-label-short">Yixun Hong</span>
              </Link>

              <div className="nav-main">
                <nav id="navLinks" className="nav-links nav-links-desktop" aria-label="Primary">
                  {navItems.map((item) =>
                    item.external ? (
                      <a
                        href={item.href}
                        key={item.href}
                        className="nav-link"
                        target="_blank"
                        rel="noreferrer"
                        onClick={resetNavigationState}
                      >
                        {item.label}
                      </a>
                    ) : (
                      <Link
                        href={item.href}
                        key={item.href}
                        className="nav-link"
                        data-active={item.active ? "true" : "false"}
                        onClick={resetNavigationState}
                      >
                        {item.label}
                      </Link>
                    )
                  )}
                </nav>

                <div className="nav-divider" aria-hidden="true" />

                <div id="inlineSearchBar" className="search-bar-container">
                  <SearchIcon className="search-bar-icon" width={18} height={18} />
                  <input
                    ref={searchInputRef}
                    type="text"
                    id="inlineSearchInput"
                    className="search-input"
                    placeholder="Search..."
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    className="search-close-btn"
                    onClick={closeSearch}
                    aria-label="Close search"
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
                            <Link
                              href={hit.url}
                              key={`${hit.type}-${hit.url}`}
                              onClick={resetNavigationState}
                            >
                              <div className="search-result-title">
                                <span className="search-result-chip">{hit.type}</span>
                                {hit.title}
                              </div>
                            </Link>
                          ))
                        ) : (
                          <div
                            style={{ padding: 12, textAlign: "center", color: "var(--muted)" }}
                          >
                            No results found.
                          </div>
                        )
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="nav-actions">
                  <button
                    type="button"
                    className="action-btn nav-mobile-trigger"
                    title={mobileMenuOpen ? "Close Menu" : "Open Menu"}
                    aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
                    aria-expanded={mobileMenuOpen}
                    onClick={() => {
                      closeSearch();
                      setMobileMenuOpen((open) => !open);
                    }}
                  >
                    {mobileMenuOpen ? <XIcon /> : <MenuIcon />}
                  </button>

                  <button
                    id="searchTrigger"
                    className="action-btn search-trigger"
                    title="Search"
                    aria-expanded={searchOpen}
                    onClick={() => {
                      setMobileMenuOpen(false);
                      setSearchOpen(true);
                    }}
                  >
                    <SearchIcon />
                  </button>

                  <button
                    id="themeToggle"
                    className="action-btn nav-theme-toggle"
                    title="Toggle Theme"
                    onClick={toggleTheme}
                  >
                    {theme === "dark" ? <SunIcon /> : <MoonIcon />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className={`nav-mobile-panel home-liquid-card${mobileMenuOpen ? " open" : ""}`}>
            <span className="home-liquid-warp nav-island-warp" aria-hidden="true" />
            <div className="nav-mobile-panel-body">
              <nav className="nav-mobile-links" aria-label="Mobile primary">
                {navItems.map((item) =>
                  item.external ? (
                    <a
                      href={item.href}
                      key={`mobile-${item.href}`}
                      className="nav-mobile-link"
                      target="_blank"
                      rel="noreferrer"
                      onClick={resetNavigationState}
                    >
                      {item.label}
                    </a>
                  ) : (
                    <Link
                      href={item.href}
                      key={`mobile-${item.href}`}
                      className="nav-mobile-link"
                      data-active={item.active ? "true" : "false"}
                      onClick={resetNavigationState}
                    >
                      {item.label}
                    </Link>
                  )
                )}
              </nav>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
