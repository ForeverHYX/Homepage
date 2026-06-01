"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import type { SearchEntry } from "@/lib/types";

type SiteSearchDropdownProps = {
  searchOpen: boolean;
  query: string;
  hits: SearchEntry[];
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  onNavigate: () => void;
};

export function SiteSearchDropdown({ searchOpen, query, hits, searchInputRef, onNavigate }: SiteSearchDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const [dropdownRect, setDropdownRect] = useState<{ left: number; top: number; width: number } | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!searchOpen) {
      setDropdownRect(null);
      return;
    }
    let cancelled = false;
    let intervalId = 0;
    const updateRect = () => {
      const input = searchInputRef.current;
      if (!input || cancelled) return;
      const rect = input.getBoundingClientRect();
      if (rect.width > 100) {
        setDropdownRect({ left: rect.left, top: rect.bottom + 8, width: rect.width });
        clearInterval(intervalId);
      }
    };
    intervalId = window.setInterval(updateRect, 50);
    const timeout = window.setTimeout(() => {
      clearInterval(intervalId);
      updateRect();
    }, 500);
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
      clearTimeout(timeout);
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [searchOpen, searchInputRef]);

  return mounted && searchOpen && dropdownRect ? createPortal(
    <div
      ref={dropdownRef}
      id="searchDropdown"
      className={`search-dropdown${query.trim() ? " has-results" : ""}`}
      style={{
        position: "fixed",
        left: dropdownRect.left,
        top: dropdownRect.top,
        width: dropdownRect.width,
        zIndex: 9999,
      }}
    >
      <div id="inlineSearchResults" style={{ padding: "8px 0" }}>
        {query.trim() ? (
          hits.length ? (
            hits.map((hit) => (
              <Link
                href={hit.url}
                key={`${hit.type}-${hit.url}`}
                onClick={onNavigate}
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
    </div>,
    document.body,
  ) : null;
}
