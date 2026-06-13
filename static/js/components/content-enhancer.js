/**
 * Content enhancer
 * ----------------
 * Runs on article detail pages that contain `.prose` blocks.
 * - Lazy-loads highlight.js (with theme-aware stylesheet) and decorates code blocks
 * - Converts GitHub repo links/URLs into rich repo cards
 */
(function () {
    "use strict";

    var HLJS_VERSION = "11.9.0";
    var HLJS_BASE =
        "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/" + HLJS_VERSION;
    var LIGHT_CSS = HLJS_BASE + "/styles/github.min.css";
    var DARK_CSS = HLJS_BASE + "/styles/github-dark.min.css";
    var HLJS_SCRIPT = HLJS_BASE + "/highlight.min.js";

    var lightLink = null;
    var darkLink = null;

    /**
     * @returns {boolean} true if the page is currently in dark theme
     */
    function isDarkTheme() {
        return document.documentElement.getAttribute("data-theme") === "dark";
    }

    /**
     * Inject the two <link> stylesheets (light + dark) and enable the right one.
     */
    function ensureThemeLinks() {
        if (!lightLink) {
            lightLink = document.createElement("link");
            lightLink.rel = "stylesheet";
            lightLink.href = LIGHT_CSS;
            document.head.appendChild(lightLink);
        }
        if (!darkLink) {
            darkLink = document.createElement("link");
            darkLink.rel = "stylesheet";
            darkLink.href = DARK_CSS;
            document.head.appendChild(darkLink);
        }
        applyThemeStyles();
    }

    /**
     * Enable/disable the two stylesheets according to the current theme.
     */
    function applyThemeStyles() {
        var dark = isDarkTheme();
        if (lightLink) lightLink.disabled = dark;
        if (darkLink) darkLink.disabled = !dark;
    }

    /**
     * Inject the highlight.js script exactly once.
     * @param {Function} cb - called once hljs is available
     */
    function loadHighlightScript(cb) {
        if (window.hljs) {
            cb();
            return;
        }
        var s = document.createElement("script");
        s.src = HLJS_SCRIPT;
        s.onload = cb;
        document.head.appendChild(s);
    }

    /**
     * Wrap every standalone <pre> in a code-block container with a header
     * (window dots + language label).
     */
    function decorateCodeBlocks() {
        document.querySelectorAll(".prose pre").forEach(function (pre) {
            // Skip if already wrapped
            if (pre.parentElement && pre.parentElement.classList.contains("code-block-container")) {
                return;
            }

            var code = pre.querySelector("code");
            var lang = "text";
            if (code) {
                Array.prototype.forEach.call(code.classList, function (cls) {
                    var m = cls.match(/^language-(.+)$/);
                    if (m) lang = m[1];
                });
            }

            // Container
            var container = document.createElement("div");
            container.className = "code-block-container";

            // Header
            var header = document.createElement("div");
            header.className = "code-header";

            // Traffic-light dots
            var dots = document.createElement("div");
            dots.className = "code-dots";

            var closeDot = document.createElement("button");
            closeDot.className = "code-dot close";
            closeDot.title = "Collapse";
            closeDot.addEventListener("click", function () {
                container.classList.toggle("collapsed");
            });

            var minDot = document.createElement("button");
            minDot.className = "code-dot min";
            minDot.title = "Minimize";

            var maxDot = document.createElement("button");
            maxDot.className = "code-dot max";
            maxDot.title = "Maximize";
            maxDot.addEventListener("click", function () {
                container.classList.toggle("maximized");
            });

            dots.appendChild(closeDot);
            dots.appendChild(minDot);
            dots.appendChild(maxDot);

            // Language label
            var langSpan = document.createElement("span");
            langSpan.className = "code-lang";
            langSpan.textContent = lang;

            header.appendChild(dots);
            header.appendChild(langSpan);

            container.appendChild(header);

            // Wrap the <pre>
            pre.parentNode.insertBefore(container, pre);
            container.appendChild(pre);
        });
    }

    // ---- GitHub repo cards -------------------------------------------------

    var GH_PATTERN = /^https:\/\/github\.com\/([^\/\s]+)\/([^\/\s?#]+)/;

    /**
     * Build the markup for a repo card from API data.
     */
    function buildRepoCard(data) {
        var card = document.createElement("a");
        card.className = "github-repo-card";
        card.href = data.html_url;
        card.target = "_blank";
        card.rel = "noopener noreferrer";

        var top = document.createElement("div");
        top.className = "github-repo-top";

        var name = document.createElement("strong");
        name.textContent = data.full_name;

        var langWrap = document.createElement("span");
        langWrap.style.display = "inline-flex";
        langWrap.style.alignItems = "center";
        langWrap.style.gap = "5px";
        langWrap.style.fontSize = "13px";
        langWrap.style.color = "var(--muted)";

        if (data.language) {
            var dot = document.createElement("span");
            dot.style.display = "inline-block";
            dot.style.width = "10px";
            dot.style.height = "10px";
            dot.style.borderRadius = "50%";
            dot.style.background = languageColor(data.language);
            langWrap.appendChild(dot);
            langWrap.appendChild(document.createTextNode(data.language));
        }

        top.appendChild(name);
        top.appendChild(langWrap);

        var desc = document.createElement("div");
        desc.className = "github-repo-desc";
        desc.textContent = data.description || "";

        var stats = document.createElement("div");
        stats.className = "github-repo-stats";

        function stat(icon, value) {
            var s = document.createElement("span");
            s.className = "github-repo-stat";
            s.innerHTML = icon + " " + (value != null ? value : "0");
            return s;
        }

        stats.appendChild(
            stat(
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:-2px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
                data.stargazers_count
            )
        );
        stats.appendChild(
            stat(
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>',
                data.forks_count
            )
        );

        card.appendChild(top);
        card.appendChild(desc);
        card.appendChild(stats);
        return card;
    }

    /**
     * Best-effort color for a few popular languages.
     */
    function languageColor(lang) {
        var map = {
            JavaScript: "#f1e05a",
            TypeScript: "#3178c6",
            Python: "#3572A5",
            Java: "#b07219",
            "C++": "#f34b7d",
            C: "#555555",
            "C#": "#178600",
            Go: "#00ADD8",
            Rust: "#dea584",
            Ruby: "#701516",
            PHP: "#4F5D95",
            Swift: "#F05138",
            Kotlin: "#A97BFF",
            HTML: "#e34c26",
            CSS: "#563d7c",
            Shell: "#89e051",
            Vue: "#41b883",
            Dart: "#00B4AB",
            Scala: "#c22d40",
            Elixir: "#6e4a7e"
        };
        return map[lang] || "#888888";
    }

    /**
     * Replace an element with a "Loading..." placeholder, fetch repo data,
     * then swap in the rendered card.
     */
    function renderRepoCard(el, owner, repo) {
        var placeholder = document.createElement("a");
        placeholder.className = "github-repo-card";
        placeholder.href = "https://github.com/" + owner + "/" + repo;
        placeholder.target = "_blank";
        placeholder.rel = "noopener noreferrer";
        placeholder.innerHTML =
            '<div class="github-repo-top"><strong>Loading...</strong></div>' +
            '<div class="github-repo-desc">Fetching repository info…</div>';

        el.parentNode.replaceChild(placeholder, el);

        fetch("https://api.github.com/repos/" + owner + "/" + repo)
            .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
            .then(function (data) {
                var card = buildRepoCard(data);
                placeholder.parentNode.replaceChild(card, placeholder);
            })
            .catch(function () {
                // On failure, leave the loading card as a fallback link
                placeholder.querySelector(".github-repo-desc").textContent =
                    "Could not load repository info.";
            });
    }

    /**
     * Scan the prose and convert GitHub links / bare GitHub URLs into cards.
     */
    function enhanceGithubLinks() {
        // 1) <a> elements whose anchor text equals the surrounding paragraph/list-item text
        document.querySelectorAll(".prose a").forEach(function (a) {
            var parent = a.parentElement;
            if (!parent || (parent.tagName !== "P" && parent.tagName !== "LI")) return;

            var match = a.href.match(GH_PATTERN);
            if (!match) return;

            // Anchor text should match parent text (i.e. link is the entire text content)
            var aText = (a.textContent || "").trim();
            var parentText = (parent.textContent || "").trim();
            if (!aText || aText !== parentText) return;

            renderRepoCard(a, match[1], match[2]);
        });

        // 2) <p>/<li> with no <a> but whose text is a bare GitHub URL
        var nodes = [];
        document.querySelectorAll(".prose p, .prose li").forEach(function (node) {
            if (node.querySelector("a")) return;
            var text = (node.textContent || "").trim();
            var m = text.match(GH_PATTERN);
            if (m) nodes.push({ node: node, owner: m[1], repo: m[2] });
        });
        nodes.forEach(function (entry) {
            renderRepoCard(entry.node, entry.owner, entry.repo);
        });
    }

    /**
     * Watch the <html> element for theme changes and re-apply stylesheets + highlighting.
     */
    function watchTheme() {
        if (!("MutationObserver" in window)) return;
        var observer = new MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].attributeName === "data-theme") {
                    applyThemeStyles();
                    if (window.hljs) window.hljs.highlightAll();
                    break;
                }
            }
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    }

    function init() {
        var prose = document.querySelector(".prose");
        if (!prose) return;

        ensureThemeLinks();
        watchTheme();

        // Load hljs, then (after a short delay for stylesheets) decorate + highlight
        loadHighlightScript(function () {
            setTimeout(function () {
                if (window.hljs) window.hljs.highlightAll();
                decorateCodeBlocks();
                enhanceGithubLinks();
            }, 60);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
