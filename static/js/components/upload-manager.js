/**
 * Upload manager
 * --------------
 * Admin file browser + uploader. Binds to elements rendered in upload.html.
 * Only runs when #uploadSidebar is present.
 */
(function () {
    "use strict";

    // ---- State -------------------------------------------------------------
    var state = {
        currentPath: "",
        queue: [],       // array of File
        uploading: false
    };

    // ---- DOM references ----------------------------------------------------
    var sidebar,
        pathLabel, fileInput, dropZone, queueInfo, startBtn,
        fileList, refreshBtn, toast,
        folderNameInput, createFolderBtn, navHomeBtn,
        metaModal, metaPath, metaTitle, metaDate, metaAuthor, metaDesc,
        metaSave, metaCancel;

    // ---- Star icon SVGs (gallery toggle) -----------------------------------
    var STAR_GRAD_DEFS =
        '<svg style="position:absolute;width:0;height:0"><defs>' +
        '<linearGradient id="star-grad" x1="0%" y1="0%" x2="100%" y2="100%">' +
        '<stop offset="0%" stop-color="#93c5fd"/>' +
        '<stop offset="100%" stop-color="#2563eb"/>' +
        '</linearGradient></defs></svg>';

    var STAR_POLYGON =
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>';

    function starOnSvg() {
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="url(#star-grad)" stroke="url(#star-grad)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + STAR_POLYGON + '</svg>';
    }

    function starOffSvg() {
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + STAR_POLYGON + '</svg>';
    }

    function ensureStarGradDefs() {
        if (!document.getElementById("star-grad")) {
            var holder = document.createElement("div");
            holder.innerHTML = STAR_GRAD_DEFS;
            document.body.appendChild(holder.firstChild);
        }
    }

    // ---- Misc helpers ------------------------------------------------------

    /**
     * Compute the parent path of a folder-like string ("a/b/c" -> "a/b").
     */
    function parentPath(path) {
        if (!path) return "";
        var idx = path.lastIndexOf("/");
        return idx < 0 ? "" : path.substring(0, idx);
    }

    /**
     * Format a byte count into a human-readable KB/MB string.
     */
    function formatSize(bytes) {
        if (bytes == null) return "";
        var kb = bytes / 1024;
        if (kb < 1024) return kb.toFixed(1) + " KB";
        return (kb / 1024).toFixed(1) + " MB";
    }

    /**
     * Small helper to build a button element with inline SVG/emoji + listener.
     */
    function iconButton(emojiOrSvg, title, onClick) {
        var btn = document.createElement("button");
        btn.className = "action-btn";
        btn.title = title;
        btn.innerHTML = emojiOrSvg;
        btn.style.padding = "4px 8px";
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            onClick();
        });
        return btn;
    }

    /**
     * Display a transient toast message.
     */
    function showToast(msg) {
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add("show");
        window.setTimeout(function () {
            toast.classList.remove("show");
        }, 2000);
    }

    /**
     * Update the path label, nav buttons, and queue info text.
     */
    function updateUI() {
        if (pathLabel) pathLabel.textContent = state.currentPath ? "/" + state.currentPath : "/";
        if (queueInfo) {
            queueInfo.textContent = state.queue.length
                ? state.queue.length + " file(s) queued"
                : "";
        }
        if (startBtn) startBtn.disabled = state.uploading || state.queue.length === 0;
    }

    // ---- File listing ------------------------------------------------------

    function fetchFiles(path) {
        return fetch("/api/files?path=" + encodeURIComponent(path), {
            credentials: "include"
        })
            .then(function (res) {
                if (res.status === 401) {
                    window.location.href = "/login";
                    return null;
                }
                return res.json();
            })
            .then(function (data) {
                if (!data) return;
                state.currentPath = data.current_path || "";
                renderFiles(data.files || []);
                updateUI();
            })
            .catch(function (err) {
                console.error("fetchFiles failed", err);
                showToast("Failed to load files");
            });
    }

    function renderFiles(files) {
        if (!fileList) return;
        fileList.innerHTML = "";
        ensureStarGradDefs();

        // Parent-directory navigation row
        if (state.currentPath) {
            var prev = document.createElement("div");
            prev.className = "file-item";
            prev.style.cursor = "pointer";
            prev.innerHTML =
                '<div class="file-icon" style="display:flex;align-items:center;gap:8px">' +
                '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/></svg>' +
                '<span>Previous Directory</span></div>';
            prev.addEventListener("click", function () {
                fetchFiles(parentPath(state.currentPath));
            });
            fileList.appendChild(prev);
        }

        files.forEach(function (item) {
            fileList.appendChild(renderFileItem(item));
        });
    }

    function renderFileItem(item) {
        var row = document.createElement("div");
        row.className = "file-item";
        row.dataset.path = item.path || "";
        row.style.display = "flex";
        row.style.alignItems = "center";
        row.style.justifyContent = "space-between";
        row.style.gap = "12px";
        row.style.padding = "10px 8px";
        row.style.borderBottom = "1px solid var(--border)";
        row.style.cursor = "default";

        var left = document.createElement("div");
        left.style.display = "flex";
        left.style.alignItems = "center";
        left.style.gap = "12px";
        left.style.minWidth = "0";
        left.style.flex = "1";

        if (item.type === "dir" || item.is_dir) {
            // ---- Directory ----
            row.style.cursor = "pointer";
            row.addEventListener("click", function () {
                fetchFiles(item.path);
            });

            var iconWrap = document.createElement("div");
            iconWrap.style.position = "relative";
            iconWrap.innerHTML =
                '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
            if (item.is_gallery) {
                var star = document.createElement("span");
                star.style.position = "absolute";
                star.style.top = "-6px";
                star.style.right = "-8px";
                star.innerHTML = starOnSvg();
                iconWrap.appendChild(star);
            }
            left.appendChild(iconWrap);

            var label = document.createElement("div");
            label.style.overflow = "hidden";
            label.style.textOverflow = "ellipsis";
            label.style.whiteSpace = "nowrap";
            var nameEl = document.createElement("div");
            nameEl.style.fontWeight = "500";
            nameEl.textContent = item.title || item.name;
            label.appendChild(nameEl);
            left.appendChild(label);

            row.appendChild(left);

            // Action buttons
            var actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "6px";
            actions.style.flexShrink = "0";

            actions.appendChild(iconButton("✎", "Edit metadata", function () {
                openMetaModal(item);
            }));

            actions.appendChild(iconButton(
                item.is_gallery ? starOnSvg() : starOffSvg(),
                item.is_gallery ? "Remove from gallery" : "Add to gallery",
                function () {
                    toggleGallery(item);
                }
            ));

            actions.appendChild(iconButton("🗑", "Delete", function () {
                deleteItem(item);
            }));

            row.appendChild(actions);

        } else {
            // ---- File ----
            var thumb = document.createElement("div");
            thumb.style.width = "40px";
            thumb.style.height = "40px";
            thumb.style.borderRadius = "6px";
            thumb.style.flexShrink = "0";
            thumb.style.background = "var(--surface-highlight)";
            thumb.style.display = "flex";
            thumb.style.alignItems = "center";
            thumb.style.justifyContent = "center";

            if (item.is_image && item.url) {
                thumb.style.backgroundImage = "url('" + item.url + "')";
                thumb.style.backgroundSize = "cover";
                thumb.style.backgroundPosition = "center";
            } else {
                thumb.innerHTML =
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
            }
            left.appendChild(thumb);

            var labelWrap = document.createElement("div");
            labelWrap.style.overflow = "hidden";
            var nameDiv = document.createElement("div");
            nameDiv.style.fontWeight = "500";
            nameDiv.style.overflow = "hidden";
            nameDiv.style.textOverflow = "ellipsis";
            nameDiv.style.whiteSpace = "nowrap";
            nameDiv.textContent = item.name;
            var sizeDiv = document.createElement("div");
            sizeDiv.style.fontSize = "12px";
            sizeDiv.style.color = "var(--muted)";
            sizeDiv.textContent = formatSize(item.size);
            labelWrap.appendChild(nameDiv);
            labelWrap.appendChild(sizeDiv);
            left.appendChild(labelWrap);

            row.appendChild(left);

            var actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "6px";
            actions.style.flexShrink = "0";

            actions.appendChild(iconButton("↗", "Open", function () {
                if (item.url) window.open(item.url, "_blank");
            }));

            actions.appendChild(iconButton("⧉", "Copy link", function () {
                if (!item.url) return;
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(item.url).then(function () {
                        showToast("Link copied");
                    });
                } else {
                    showToast(item.url);
                }
            }));

            actions.appendChild(iconButton("🗑", "Delete", function () {
                deleteItem(item);
            }));

            row.appendChild(actions);
        }

        return row;
    }

    // ---- Mutations ---------------------------------------------------------

    function refresh() {
        return fetchFiles(state.currentPath);
    }

    function deleteItem(item) {
        if (!confirm("Delete '" + (item.name || item.title || item.path) + "'?")) return;
        fetch("/api/files/" + encodeURIComponent(item.path), {
            method: "DELETE",
            credentials: "include"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("Delete failed");
                showToast("Deleted");
                refresh();
            })
            .catch(function (err) {
                console.error(err);
                showToast("Delete failed");
            });
    }

    function toggleGallery(item) {
        var formData = new FormData();
        formData.append("path", item.path);
        formData.append("enable", item.is_gallery ? "false" : "true");

        fetch("/api/gallery/toggle", {
            method: "POST",
            body: formData,
            credentials: "include"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("Toggle failed");
                return refresh().then(function () {
                    // Briefly highlight the affected row
                    var row = fileList.querySelector('.file-item[data-path="' + cssEscape(item.path) + '"]');
                    if (row) {
                        row.style.transition = "background 0.3s";
                        row.style.background = "var(--surface-highlight)";
                        window.setTimeout(function () {
                            row.style.background = "";
                        }, 1500);
                    }
                });
            })
            .catch(function (err) {
                console.error(err);
                showToast("Toggle failed");
            });
    }

    // Minimal CSS escape for attribute selectors
    function cssEscape(s) {
        return String(s).replace(/(["\\])/g, "\\$1");
    }

    // ---- Upload ------------------------------------------------------------

    function addFilesToQueue(fileListObj) {
        Array.prototype.forEach.call(fileListObj, function (f) {
            state.queue.push(f);
        });
        updateUI();
    }

    function clearQueue() {
        state.queue = [];
        updateUI();
    }

    function startUpload() {
        if (state.uploading || state.queue.length === 0) return;
        state.uploading = true;
        var originalText = startBtn.textContent;
        startBtn.textContent = "Uploading...";
        updateUI();

        // Sequential upload to keep things simple and predictable
        var queue = state.queue.slice();
        var i = 0;

        function next() {
            if (i >= queue.length) {
                state.uploading = false;
                startBtn.textContent = originalText;
                clearQueue();
                refresh();
                showToast("Upload complete");
                return;
            }
            var file = queue[i++];
            var formData = new FormData();
            formData.append("file", file);
            formData.append("path", state.currentPath);

            fetch("/api/upload", {
                method: "POST",
                body: formData,
                credentials: "include"
            })
                .then(function (res) {
                    if (!res.ok) throw new Error("Upload failed for " + file.name);
                    next();
                })
                .catch(function (err) {
                    console.error(err);
                    state.uploading = false;
                    startBtn.textContent = originalText;
                    updateUI();
                    showToast("Upload failed");
                });
        }

        next();
    }

    // ---- Folder operations -------------------------------------------------

    function createFolder() {
        var name = (folderNameInput.value || "").trim();
        if (!name) return;
        var formData = new FormData();
        formData.append("name", name);
        formData.append("path", state.currentPath);

        fetch("/api/folder", {
            method: "POST",
            body: formData,
            credentials: "include"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("Create folder failed");
                folderNameInput.value = "";
                refresh();
                showToast("Folder created");
            })
            .catch(function (err) {
                console.error(err);
                showToast("Failed to create folder");
            });
    }

    // ---- Metadata modal ----------------------------------------------------

    function openMetaModal(item) {
        if (!metaModal) return;
        metaPath.value = item.path || "";
        metaTitle.value = item.title || "";
        metaDate.value = item.date || "";
        metaAuthor.value = item.author || "";
        metaDesc.value = item.desc || "";
        // Use the .active class so the .lightbox-overlay opacity transition
        // (opacity:0 -> 1) applies. Setting display alone leaves it invisible.
        metaModal.classList.add("active");
        metaModal.style.display = "";
    }

    function closeMetaModal() {
        if (metaModal) {
            metaModal.classList.remove("active");
            metaModal.style.display = "none";
        }
    }

    function saveMeta() {
        var formData = new FormData();
        formData.append("path", metaPath.value);
        formData.append("title", metaTitle.value);
        formData.append("date", metaDate.value);
        formData.append("author", metaAuthor.value);
        // API Form field is named "description" (upload.py), not "desc".
        // The list payload maps it to "desc" for display only.
        formData.append("description", metaDesc.value);

        fetch("/api/folder/meta", {
            method: "POST",
            body: formData,
            credentials: "include"
        })
            .then(function (res) {
                if (!res.ok) throw new Error("Save meta failed");
                closeMetaModal();
                refresh();
                showToast("Saved");
            })
            .catch(function (err) {
                console.error(err);
                showToast("Save failed");
            });
    }

    // ---- Drag & drop -------------------------------------------------------

    function setupDropZone() {
        if (!dropZone) return;

        // Click opens file dialog
        dropZone.addEventListener("click", function () {
            if (fileInput) fileInput.click();
        });

        // Drag styling + drop
        dropZone.addEventListener("dragover", function (e) {
            e.preventDefault();
            dropZone.style.borderColor = "var(--primary)";
            dropZone.style.background = "var(--surface-highlight)";
        });

        dropZone.addEventListener("dragleave", function (e) {
            e.preventDefault();
            dropZone.style.borderColor = "";
            dropZone.style.background = "transparent";
        });

        dropZone.addEventListener("drop", function (e) {
            e.preventDefault();
            dropZone.style.borderColor = "";
            dropZone.style.background = "transparent";
            if (e.dataTransfer && e.dataTransfer.files) {
                addFilesToQueue(e.dataTransfer.files);
            }
        });
    }

    // ---- Bootstrap ---------------------------------------------------------

    function bindElements() {
        sidebar = document.getElementById("uploadSidebar");
        if (!sidebar) return false;

        pathLabel = document.getElementById("currentPathLabel");
        fileInput = document.getElementById("fileInput");
        dropZone = document.getElementById("dropZone");
        queueInfo = document.getElementById("queueInfo");
        startBtn = document.getElementById("startUploadBtn");
        fileList = document.getElementById("fileList");
        refreshBtn = document.getElementById("refreshBtn");
        toast = document.getElementById("toast");
        folderNameInput = document.getElementById("folderName");
        createFolderBtn = document.getElementById("createFolderBtn");
        navHomeBtn = document.querySelector("[data-nav-home]");

        metaModal = document.getElementById("metaModal");
        metaPath = document.getElementById("metaPath");
        metaTitle = document.getElementById("metaTitle");
        metaDate = document.getElementById("metaDate");
        metaAuthor = document.getElementById("metaAuthor");
        metaDesc = document.getElementById("metaDesc");
        metaSave = document.getElementById("metaSave");
        metaCancel = document.getElementById("metaCancel");

        return true;
    }

    function bindEvents() {
        if (refreshBtn) refreshBtn.addEventListener("click", refresh);
        if (startBtn) startBtn.addEventListener("click", startUpload);
        if (createFolderBtn) createFolderBtn.addEventListener("click", createFolder);
        if (navHomeBtn) navHomeBtn.addEventListener("click", function () { fetchFiles(""); });

        if (fileInput) {
            fileInput.addEventListener("change", function () {
                if (fileInput.files) addFilesToQueue(fileInput.files);
                fileInput.value = "";
            });
        }

        setupDropZone();

        // Metadata modal
        if (metaSave) metaSave.addEventListener("click", saveMeta);
        if (metaCancel) metaCancel.addEventListener("click", closeMetaModal);
        if (metaModal) {
            metaModal.addEventListener("click", function (e) {
                // Only close when clicking the overlay itself, not its children
                if (e.target === metaModal) closeMetaModal();
            });
        }

        // Enter-to-create folder
        if (folderNameInput) {
            folderNameInput.addEventListener("keydown", function (e) {
                if (e.key === "Enter") createFolder();
            });
        }
    }

    function init() {
        if (!bindElements()) return;
        bindEvents();
        ensureStarGradDefs();
        updateUI();
        fetchFiles("");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
