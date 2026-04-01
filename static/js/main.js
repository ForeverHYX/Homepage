
    document.getElementById('copyright-year').textContent = new Date().getFullYear();
    const ICON_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    const ICON_SUN = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

    function toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    }
    
    function updateThemeIcon(theme) {
        const btn = document.getElementById('themeToggle');
        if (theme === 'dark') {
            btn.innerHTML = ICON_SUN;
            document.getElementById('hljs-light').disabled = true;
            document.getElementById('hljs-dark').disabled = false;
        } else {
            btn.innerHTML = ICON_MOON;
            document.getElementById('hljs-dark').disabled = true;
            document.getElementById('hljs-light').disabled = false;
        }
    }
    
    // Search Logic (Inline)
    let searchIndex = null;
    const headerEl = document.querySelector('header .container');
    
    function openSearch() {
        headerEl.classList.add('search-mode');
        setTimeout(() => document.getElementById('inlineSearchInput').focus(), 100);
        
        if (!searchIndex) {
            fetch('/api/search-index')
                .then(r => r.json())
                .then(data => { searchIndex = data; })
                .catch(e => console.error("Search failed", e));
        }
    }
    
    function closeSearch() {
        headerEl.classList.remove('search-mode');
        document.getElementById('searchDropdown').classList.remove('has-results');
        setTimeout(() => {
             document.getElementById('inlineSearchInput').value = '';
        }, 300);
    }
    
    function doSearch() {
        const q = document.getElementById('inlineSearchInput').value.toLowerCase().trim();
        const res = document.getElementById('inlineSearchResults');
        const dropdown = document.getElementById('searchDropdown');
        
        if (q.length < 1) { 
            dropdown.classList.remove('has-results');
            return; 
        }
        
        if (!searchIndex) return;
        
        const hits = searchIndex.filter(item => 
            (item.title && item.title.toLowerCase().includes(q)) || 
            (item.desc && item.desc.toLowerCase().includes(q)) ||
            (item.tags && item.tags.some(t => t.toLowerCase().includes(q)))
        );
        
        if (hits.length === 0) {
            res.innerHTML = '<div style="padding:12px; text-align:center; color:var(--muted);">No results found.</div>';
            dropdown.classList.add('has-results');
            return;
        }
        
        res.innerHTML = hits.map(h => `
            <a href="${h.url}" onclick="closeSearch()" style="display:block; text-decoration:none; padding:10px 16px; border-bottom:1px solid var(--border); transition:background .2s;" onmouseover="this.style.background='var(--surface-highlight)'" onmouseout="this.style.background='transparent'">
                <div style="color:var(--heading); font-weight:600; font-size:14px; display:flex; align-items:center;">
                    <span style="font-size:11px; background:var(--surface-highlight); color:var(--primary); padding:2px 6px; border-radius:4px; margin-right:8px;">${h.type}</span>
                    ${h.title}
                </div>
            </a>
        `).join('');
        
        dropdown.classList.add('has-results');
    }

    // Init correct icon on load
    updateThemeIcon(document.documentElement.getAttribute('data-theme'));
    
    // Transform code blocks to add interactive Mac-style headers
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.prose pre').forEach((pre) => {
            if (!pre.parentNode || pre.closest('.code-block-container')) return;

            let lang = 'code';
            const code = pre.querySelector('code');
            if (code) {
                code.classList.forEach((cls) => {
                    if (cls.startsWith('language-')) {
                        lang = cls.replace('language-', '');
                    }
                });
            }
            if (!lang || lang === 'undefined' || lang === 'hljs') {
                lang = 'text';
            }

            const container = document.createElement('div');
            container.className = 'code-block-container';

            const header = document.createElement('div');
            header.className = 'code-header';

            const dots = document.createElement('div');
            dots.className = 'code-dots';

            const btnClose = document.createElement('button');
            btnClose.className = 'code-dot close';
            btnClose.title = 'Collapse';
            btnClose.onclick = () => { container.classList.toggle('collapsed'); };

            const btnMin = document.createElement('button');
            btnMin.className = 'code-dot min';

            const btnMax = document.createElement('button');
            btnMax.className = 'code-dot max';
            btnMax.title = 'Maximize';
            btnMax.onclick = () => { container.classList.toggle('maximized'); };

            dots.appendChild(btnClose);
            dots.appendChild(btnMin);
            dots.appendChild(btnMax);

            const langLabel = document.createElement('span');
            langLabel.className = 'code-lang';
            langLabel.textContent = lang;

            header.appendChild(dots);
            header.appendChild(langLabel);

            const wrapper = document.createElement('div');
            wrapper.className = 'code-content-wrapper';

            pre.parentNode.insertBefore(container, pre);
            container.appendChild(header);
            container.appendChild(wrapper);
            wrapper.appendChild(pre);
        });
    });
    
    // Global Event to close search if clicking outside
    document.addEventListener('click', (e) => {
        if (headerEl.classList.contains('search-mode')) {
            if (!document.getElementById('inlineSearchBar').contains(e.target) && !document.getElementById('searchTrigger').contains(e.target)) {
                closeSearch();
            }
        }
    });
    
    // Auto-convert standalone GitHub links into Repo Cards
    document.addEventListener('DOMContentLoaded', () => {
        const escapeHtml = (s) => String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

        const githubRegex = /^https?:\/\/github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)\/?$/;

        const renderGithubCard = (parent, owner, repo) => {
            parent.innerHTML = '<div class="github-repo-card" style="opacity:0.6; padding: 12px 16px;"><div class="github-repo-top" style="margin:0;">Loading GitHub Repo: ' + owner + '/' + repo + '...</div></div>';

            fetch('https://api.github.com/repos/' + owner + '/' + repo)
                .then((res) => res.json())
                .then((data) => {
                    if (data.message && data.message === 'Not Found') {
                        parent.innerHTML = '<a href="https://github.com/' + owner + '/' + repo + '">https://github.com/' + owner + '/' + repo + '</a>';
                        return;
                    }

                    const descHtml = data.description
                        ? '<div class="github-repo-desc">' + escapeHtml(data.description) + '</div>'
                        : '';

                    const langHtml = data.language
                        ? '<div class="github-repo-stat"><span style="width:10px;height:10px;border-radius:50%;background:var(--primary);display:inline-block;"></span>' + escapeHtml(data.language) + '</div>'
                        : '';

                    parent.outerHTML =
                        '<a href="' + escapeHtml(data.html_url) + '" target="_blank" class="github-repo-card">' +
                            '<div class="github-repo-top">' +
                                '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>' +
                                '<span>' + escapeHtml(data.full_name) + '</span>' +
                            '</div>' +
                            descHtml +
                            '<div class="github-repo-stats">' +
                                langHtml +
                                '<div class="github-repo-stat">' +
                                    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
                                    String(data.stargazers_count ?? 0) +
                                '</div>' +
                                '<div class="github-repo-stat">' +
                                    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>' +
                                    String(data.forks_count ?? 0) +
                                '</div>' +
                            '</div>' +
                        '</a>';
                })
                .catch(() => {
                    parent.innerHTML = '<a href="https://github.com/' + owner + '/' + repo + '">https://github.com/' + owner + '/' + repo + '</a>';
                });
        };

        // Case A: markdown already rendered as anchor
        document.querySelectorAll('.prose a').forEach((a) => {
            const parent = a.parentNode;
            if (!parent) return;
            if (!(parent.tagName === 'P' || parent.tagName === 'LI')) return;
            if (parent.textContent.trim() !== a.textContent.trim()) return;

            const match = a.href.match(githubRegex);
            if (!match) return;
            renderGithubCard(parent, match[1], match[2]);
        });

        // Case B: markdown kept as plain text URL
        document.querySelectorAll('.prose p, .prose li').forEach((node) => {
            if (node.querySelector('a')) return;
            const text = node.textContent.trim();
            const match = text.match(githubRegex);
            if (!match) return;
            renderGithubCard(node, match[1], match[2]);
        });
    });
  
    {script}
  