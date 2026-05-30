/* eslint-disable @next/next/no-img-element */
"use client";

import Link from "next/link";
import { CalendarIcon, UserIcon } from "@/components/icons";
import { useEffect, useState } from "react";
import type { GalleryAlbum } from "@/lib/types";

type GalleryViewProps = {
  albums: GalleryAlbum[];
  isFocused: boolean;
};

export function GalleryView({ albums, isFocused }: GalleryViewProps) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  useEffect(() => {
    if (isFocused) {
      return;
    }

    const containers = Array.from(
      document.querySelectorAll<HTMLElement>(".carousel-container")
    );
    const intervals: number[] = [];

    containers.forEach((container) => {
      let interval = window.setInterval(() => {
        const currentScroll = container.scrollLeft;
        const maxScroll = container.scrollWidth - container.clientWidth;
        if (currentScroll >= maxScroll - 5) {
          container.scrollTo({ left: 0, behavior: "smooth" });
        } else {
          container.scrollBy({ left: 400, behavior: "smooth" });
        }
      }, 2000);

      const stop = () => {
        window.clearInterval(interval);
      };
      const start = () => {
        stop();
        interval = window.setInterval(() => {
          const currentScroll = container.scrollLeft;
          const maxScroll = container.scrollWidth - container.clientWidth;
          if (currentScroll >= maxScroll - 5) {
            container.scrollTo({ left: 0, behavior: "smooth" });
          } else {
            container.scrollBy({ left: 400, behavior: "smooth" });
          }
        }, 2000);
      };

      container.addEventListener("mouseenter", stop);
      container.addEventListener("mouseleave", start);
      container.addEventListener("touchstart", stop, { passive: true });
      container.addEventListener("touchend", start);
      intervals.push(interval);
    });

    return () => intervals.forEach((interval) => window.clearInterval(interval));
  }, [isFocused]);

  return (
    <div className="container">
      <div className="page-shell">
        <div className="gallery-list">
          {albums.length ? (
            albums.map((album) => (
              <section
                className="gallery-album mb-12"
                style={{
                  marginBottom: isFocused ? 60 : 24,
                }}
                key={album.rel_path}
              >
                {isFocused ? (
                  <div className="card home-liquid-card">
                    <span className="home-liquid-warp" aria-hidden="true" />
                    <div className="home-liquid-body" style={{ padding: 40 }}>
                      <div style={{ marginBottom: 20 }}>
                        <Link
                          href="/gallery"
                          className="action-btn"
                          style={{
                            textDecoration: "none",
                            paddingLeft: 0,
                            color: "var(--text)",
                            fontWeight: 500,
                          }}
                        >
                          &larr; Back to All Galleries
                        </Link>
                      </div>

                      <h2
                        style={{
                          fontSize: "2.5rem",
                          fontWeight: 600,
                          margin: "0 0 12px 0",
                          textTransform: "capitalize",
                          lineHeight: 1.2,
                          color: "var(--heading)",
                        }}
                      >
                        {album.title}
                      </h2>
                      <div
                        style={{
                          display: "flex",
                          gap: 24,
                          color: "var(--muted)",
                          fontSize: 15,
                          marginBottom: 12,
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <span><CalendarIcon width={14} height={14} /> {album.date_str}</span>
                        <span><UserIcon width={14} height={14} /> {album.author}</span>
                      </div>
                      {album.desc ? (
                        <p
                          style={{
                            color: "var(--text)",
                            fontSize: "1rem",
                            margin: "0 0 24px 0",
                            lineHeight: 1.6,
                          }}
                        >
                          {album.desc}
                        </p>
                      ) : null}

                      <div
                        className={album.wrapper_class}
                        style={{ boxShadow: "none", border: "none", padding: 0, background: "transparent" }}
                      >
                        <div className="carousel-container" id={`carousel-${album.path_name}`}>
                          {album.images.map((imageUrl) => (
                            <div
                              className="carousel-slide"
                              onClick={() => setLightboxUrl(imageUrl)}
                              key={imageUrl}
                            >
                              <img src={imageUrl} loading="lazy" alt="Photo" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="card home-glass">
                    <div className="home-glass-body" style={{ padding: "28px 32px" }}>
                      <div style={{ marginBottom: 16 }}>
                        <h2
                          style={{
                            fontSize: "1.5rem",
                            fontWeight: 700,
                            margin: "0 0 12px 0",
                            textTransform: "capitalize",
                            lineHeight: 1.2,
                            color: "var(--heading)",
                          }}
                        >
                          <Link href={`/gallery?focus=${encodeURIComponent(album.rel_path)}`}>
                            {album.title}
                          </Link>
                        </h2>
                        <div
                          style={{
                            display: "flex",
                            gap: 16,
                            color: "var(--muted)",
                            fontSize: 13,
                            marginBottom: 12,
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <span><CalendarIcon width={14} height={14} /> {album.date_str}</span>
                          <span><UserIcon width={14} height={14} /> {album.author}</span>
                        </div>
                        {album.desc ? (
                          <p
                            style={{
                              color: "var(--text)",
                              fontSize: 15,
                              margin: "0 0 16px 0",
                              lineHeight: 1.6,
                            }}
                          >
                            {album.desc}
                          </p>
                        ) : null}
                      </div>

                      <div
                        className={album.wrapper_class}
                        style={{ boxShadow: "none", border: "none", padding: 0, background: "transparent" }}
                      >
                        <div className="carousel-container" id={`carousel-${album.path_name}`}>
                          {album.images.map((imageUrl) => (
                            <div
                              className="carousel-slide"
                              onClick={() => setLightboxUrl(imageUrl)}
                              key={imageUrl}
                            >
                              <img src={imageUrl} loading="lazy" alt="Photo" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </section>
            ))
          ) : (
            <p>No albums found.</p>
          )}
        </div>
      </div>

      <div
        id="lightboxOverlay"
        className={`lightbox-overlay${lightboxUrl ? " active" : ""}`}
        onClick={() => setLightboxUrl(null)}
        style={{ display: lightboxUrl ? "flex" : "none" }}
      >
        <button className="lightbox-close" onClick={() => setLightboxUrl(null)}>
          &times;
        </button>
        <img
          id="lightboxImg"
          className="lightbox-content"
          src={lightboxUrl ?? ""}
          alt="Full Size"
          onClick={(event) => event.stopPropagation()}
        />
      </div>
    </div>
  );
}
