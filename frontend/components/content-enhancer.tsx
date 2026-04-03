"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { useActiveTheme } from "@/components/use-active-theme";

declare global {
  interface Window {
    hljs?: {
      highlightAll: () => void;
    };
  }
}

export function ContentEnhancer() {
  const pathname = usePathname();
  const theme = useActiveTheme();

  useEffect(() => {
    const lightSheet = document.getElementById("hljs-light") as HTMLLinkElement | null;
    const darkSheet = document.getElementById("hljs-dark") as HTMLLinkElement | null;
    if (lightSheet && darkSheet) {
      if (theme === "dark") {
        lightSheet.disabled = true;
        darkSheet.disabled = false;
      } else {
        darkSheet.disabled = true;
        lightSheet.disabled = false;
      }
    }

    window.setTimeout(() => {
      window.hljs?.highlightAll();

      document.querySelectorAll(".prose pre").forEach((pre) => {
        if (!pre.parentNode || pre.closest(".code-block-container")) {
          return;
        }

        let lang = "text";
        const code = pre.querySelector("code");
        if (code) {
          code.classList.forEach((className) => {
            if (className.startsWith("language-")) {
              lang = className.replace("language-", "");
            }
          });
        }

        const container = document.createElement("div");
        container.className = "code-block-container";

        const header = document.createElement("div");
        header.className = "code-header";

        const dots = document.createElement("div");
        dots.className = "code-dots";

        const btnClose = document.createElement("button");
        btnClose.className = "code-dot close";
        btnClose.title = "Collapse";
        btnClose.onclick = () => {
          container.classList.toggle("collapsed");
        };

        const btnMin = document.createElement("button");
        btnMin.className = "code-dot min";

        const btnMax = document.createElement("button");
        btnMax.className = "code-dot max";
        btnMax.title = "Maximize";
        btnMax.onclick = () => {
          container.classList.toggle("maximized");
        };

        dots.appendChild(btnClose);
        dots.appendChild(btnMin);
        dots.appendChild(btnMax);

        const langLabel = document.createElement("span");
        langLabel.className = "code-lang";
        langLabel.textContent = lang || "text";

        header.appendChild(dots);
        header.appendChild(langLabel);

        const wrapper = document.createElement("div");
        wrapper.className = "code-content-wrapper";

        pre.parentNode.insertBefore(container, pre);
        container.appendChild(header);
        container.appendChild(wrapper);
        wrapper.appendChild(pre);
      });

      const escapeHtml = (value: string) =>
        String(value)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      const githubRegex = /^https?:\/\/github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)\/?$/;

      const renderGithubCard = (parent: Element, owner: string, repo: string) => {
        parent.innerHTML =
          '<div class="github-repo-card" style="opacity:0.6; padding: 12px 16px;"><div class="github-repo-top" style="margin:0;">Loading GitHub Repo: ' +
          owner +
          "/" +
          repo +
          "...</div></div>";

        fetch("https://api.github.com/repos/" + owner + "/" + repo)
          .then((response) => response.json())
          .then((data) => {
            if (data.message === "Not Found") {
              parent.innerHTML =
                '<a href="https://github.com/' + owner + "/" + repo + '">https://github.com/' + owner + "/" + repo + "</a>";
              return;
            }

            const descHtml = data.description
              ? '<div class="github-repo-desc">' + escapeHtml(data.description) + "</div>"
              : "";

            const langHtml = data.language
              ? '<div class="github-repo-stat"><span style="width:10px;height:10px;border-radius:50%;background:var(--primary);display:inline-block;"></span>' +
                escapeHtml(data.language) +
                "</div>"
              : "";

            parent.outerHTML =
              '<a href="' +
              escapeHtml(data.html_url) +
              '" target="_blank" class="github-repo-card">' +
              '<div class="github-repo-top">' +
              '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>' +
              "<span>" +
              escapeHtml(data.full_name) +
              "</span>" +
              "</div>" +
              descHtml +
              '<div class="github-repo-stats">' +
              langHtml +
              '<div class="github-repo-stat"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
              String(data.stargazers_count ?? 0) +
              "</div>" +
              '<div class="github-repo-stat"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>' +
              String(data.forks_count ?? 0) +
              "</div>" +
              "</div>" +
              "</a>";
          })
          .catch(() => {
            parent.innerHTML =
              '<a href="https://github.com/' + owner + "/" + repo + '">https://github.com/' + owner + "/" + repo + "</a>";
          });
      };

      document.querySelectorAll(".prose a").forEach((anchor) => {
        const parent = anchor.parentElement;
        if (!parent) {
          return;
        }
        if (!(parent.tagName === "P" || parent.tagName === "LI")) {
          return;
        }
        if (parent.textContent?.trim() !== anchor.textContent?.trim()) {
          return;
        }

        const match = anchor.getAttribute("href")?.match(githubRegex);
        if (!match) {
          return;
        }
        renderGithubCard(parent, match[1], match[2]);
      });

      document.querySelectorAll(".prose p, .prose li").forEach((node) => {
        if (node.querySelector("a")) {
          return;
        }
        const text = node.textContent?.trim() ?? "";
        const match = text.match(githubRegex);
        if (!match) {
          return;
        }
        renderGithubCard(node, match[1], match[2]);
      });
    }, 60);
  }, [pathname, theme]);

  return null;
}
