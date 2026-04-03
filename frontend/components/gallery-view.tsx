/* eslint-disable @next/next/no-img-element */
"use client";

import Link from "next/link";
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
        {!isFocused ? (
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
              Gallery
            </h1>
            <p className="page-lead">Travel photos, portraits, and moments.</p>
          </div>
        ) : null}

        <div className="gallery-list">
          {albums.length ? (
            albums.map((album) => (
              <section
                className="gallery-album mb-12 card"
                style={{
                  padding: isFocused ? 40 : 24,
                  marginBottom: isFocused ? 60 : 24,
                }}
                key={album.rel_path}
              >
                {isFocused ? (
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
                ) : null}

                <div style={{ marginBottom: isFocused ? 24 : 16 }}>
                  <h2
                    style={{
                      fontSize: isFocused ? "2.5rem" : "1.5rem",
                      fontWeight: isFocused ? 600 : 700,
                      margin: "0 0 12px 0",
                      textTransform: "capitalize",
                      lineHeight: 1.2,
                      color: "var(--heading)",
                      borderLeft: isFocused ? "6px solid var(--primary)" : undefined,
                      paddingLeft: isFocused ? 16 : undefined,
                    }}
                  >
                    {isFocused ? (
                      album.title
                    ) : (
                      <Link href={`/gallery?focus=${encodeURIComponent(album.rel_path)}`}>
                        {album.title}
                      </Link>
                    )}
                  </h2>
                  <div
                    style={{
                      display: "flex",
                      gap: isFocused ? 24 : 16,
                      color: "var(--muted)",
                      fontSize: isFocused ? 15 : 13,
                      paddingLeft: isFocused ? 22 : 0,
                      marginBottom: 12,
                      alignItems: "center",
                      flexWrap: "wrap",
                    }}
                  >
                    <span>{album.date_str}</span>
                    <span>{album.author}</span>
                  </div>
                  {album.desc ? (
                    <p
                      style={{
                        color: "var(--text)",
                        fontSize: isFocused ? "1rem" : 15,
                        margin: "0 0 16px 0",
                        lineHeight: 1.6,
                        paddingLeft: isFocused ? 22 : 0,
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
