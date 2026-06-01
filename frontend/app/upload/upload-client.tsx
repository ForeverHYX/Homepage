"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface FileItem {
  name: string;
  type: "file" | "dir";
  size?: number;
  url?: string;
  is_gallery?: boolean;
  path: string;
  title?: string;
  description?: string;
  date?: string;
  author?: string;
}

function getIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  return ["jpg", "jpeg", "png", "gif", "webp"].includes(ext) ? "img" : "file";
}

export default function UploadManager() {
  const [currentPath, setCurrentPath] = useState("");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [queue, setQueue] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [modalData, setModalData] = useState({ path: "", title: "", description: "", date: "", author: "Yixun Hong" });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2000);
  }, []);

  const fetchFiles = useCallback(async (path: string) => {
    setCurrentPath(path);
    try {
      const res = await fetch(`/api/files?path=${encodeURIComponent(path)}`, { credentials: "include" });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setFiles(data.files || []);
    } catch (e: any) {
      setFiles([]);
      showToast(`Error: ${e.message}`);
    }
  }, [showToast]);

  useEffect(() => {
    fetchFiles("");
  }, [fetchFiles]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) {
      setQueue((prev) => [...prev, ...Array.from(e.dataTransfer.files)]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setQueue((prev) => [...prev, ...Array.from(e.target.files as FileList)]);
    }
  };

  const startUpload = async () => {
    if (!queue.length) return;
    setUploading(true);
    try {
      for (const f of queue) {
        const form = new FormData();
        form.append("file", f);
        form.append("path", currentPath);
        const res = await fetch("/api/upload", { method: "POST", body: form, credentials: "include" });
        if (!res.ok) {
          const txt = await res.text();
          console.error("Upload failed", res.status, txt);
          alert(`Upload failed: ${res.status}`);
        }
      }
      showToast("Upload Complete");
    } catch (e: any) {
      alert(`Network error: ${e}`);
    } finally {
      setQueue([]);
      setUploading(false);
      fetchFiles(currentPath);
    }
  };

  const createFolder = async () => {
    const name = (document.getElementById("folderName") as HTMLInputElement)?.value.trim();
    if (!name) return;
    const form = new FormData();
    form.append("name", name);
    form.append("path", currentPath);
    await fetch("/api/folder", { method: "POST", body: form, credentials: "include" });
    (document.getElementById("folderName") as HTMLInputElement).value = "";
    fetchFiles(currentPath);
  };

const deleteItem = async (path: string) => {
    if (!confirm(`Permanently delete ${path}? Folder contents will be lost.`)) return;
    try {
const res = await fetch(`/api/files/${encodeURIComponent(path)}`, { method: "DELETE", credentials: "include" });
if (res.ok) {
showToast("Deleted");
fetchFiles(currentPath);
    } else {
        const data = await res.json().catch(() => ({}));
        showToast(`Delete failed: ${data.detail || res.statusText}`);
      }
    } catch (e: any) {
      showToast(`Delete failed: ${e.message}`);
    }
};

  const openMeta = (item: FileItem) => {
    setModalData({
      path: item.path,
      title: item.title || item.name,
      description: item.description || "",
      date: item.date || "",
      author: item.author || "Yixun Hong",
    });
    setEditMode(true);
  };

  const closeMeta = () => {
    setEditMode(false);
    setModalData({ path: "", title: "", description: "", date: "", author: "Yixun Hong" });
  };

  const saveMeta = async () => {
    const form = new FormData();
    form.append("path", modalData.path);
    form.append("title", modalData.title);
    form.append("description", modalData.description);
    form.append("date", modalData.date);
    form.append("author", modalData.author);
    await fetch("/api/folder/meta", { method: "POST", body: form, credentials: "include" });
    closeMeta();
    fetchFiles(currentPath);
    showToast("Info Updated");
  };

  const toggleGallery = async (path: string, enable: boolean) => {
    const form = new FormData();
    form.append("path", path);
    form.append("enable", String(enable));
    await fetch("/api/gallery/toggle", { method: "POST", body: form, credentials: "include" });
    fetchFiles(currentPath);
    showToast("Gallery Updated");
  };

  const parentPath = currentPath ? currentPath.split("/").slice(0, -1).join("/") : "";

  return (
    <div className="container upload-grid">
      <section>
        <div className="card" style={{ padding: "24px", position: "sticky", top: "100px" }}>
          {editMode ? (
            <>
              <h2 style={{ marginTop: 0, fontSize: "18px", color: "var(--heading)" }}>Edit Folder Info</h2>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Title</label>
                <input value={modalData.title} onChange={(e) => setModalData({ ...modalData, title: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} />
              </div>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Shoot Date</label>
                <input type="date" value={modalData.date} onChange={(e) => setModalData({ ...modalData, date: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} />
              </div>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Author</label>
                <input value={modalData.author} onChange={(e) => setModalData({ ...modalData, author: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }} placeholder="Yixun Hong" />
              </div>
              <div style={{ marginBottom: "20px" }}>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: 500, color: "var(--text)" }}>Description</label>
                <textarea rows={3} value={modalData.description} onChange={(e) => setModalData({ ...modalData, description: e.target.value })} style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)", fontFamily: "inherit" }} />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button className="btn" style={{ background: "var(--surface-highlight)", color: "var(--text)" }} onClick={closeMeta}>Cancel</button>
                <button className="btn btn-primary" onClick={saveMeta}>Save</button>
              </div>
            </>
          ) : (
            <>
              <h2 style={{ marginTop: 0, fontSize: "18px", color: "var(--heading)" }}>Upload Manager</h2>

              <div style={{ marginBottom: "16px" }}>
                <div style={{ fontWeight: 600, marginBottom: "8px", fontSize: "14px", color: "var(--muted)" }}>Current Path:</div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center", background: "var(--surface-highlight)", padding: "8px", borderRadius: "6px", fontFamily: "monospace", overflowX: "auto" }}>
                  <button className="action-btn" onClick={() => fetchFiles("")}>Home</button>
                  <span>{currentPath ? "/ " + currentPath : "/"}</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
                <input
                  id="folderName"
                  type="text"
                  placeholder="New Folder"
                  style={{ width: "100%", padding: "8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface)", color: "var(--text)" }}
                />
                <button className="btn btn-primary" onClick={createFolder} style={{ padding: "0 12px" }}>+</button>
              </div>

              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: dragOver ? "2px dashed var(--primary)" : "2px dashed var(--border)",
                  borderRadius: "12px",
                  padding: "24px",
                  textAlign: "center",
                  background: dragOver ? "var(--surface-highlight)" : "transparent",
                  transition: "all 0.2s",
                  cursor: "pointer",
                }}
              >
                <div style={{ color: "var(--primary)", marginBottom: "12px" }}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <p style={{ margin: 0, fontWeight: 600, color: "var(--text)", fontSize: "15px" }}>Click to Add Files</p>
                <input ref={fileInputRef} type="file" multiple onChange={handleFileSelect} style={{ display: "none" }} />
              </div>

              <div style={{ marginTop: "16px", fontSize: "14px", textAlign: "center", color: "var(--muted)" }}>
                {queue.length ? `${queue.length} file(s) ready` : ""}
              </div>
              <button className="btn btn-primary" style={{ marginTop: "16px", width: "100%" }} disabled={!queue.length || uploading} onClick={startUpload}>
                {uploading ? "Uploading..." : "Start Upload"}
              </button>
            </>
          )}
        </div>
      </section>

      <section>
        <div className="card" style={{ padding: "32px", minHeight: "400px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
            <h2 style={{ margin: 0, fontSize: "20px", color: "var(--heading)" }}>Files &amp; Folders</h2>
            <button className="action-btn" onClick={() => fetchFiles(currentPath)}>Refresh</button>
          </div>

          <div>
            {currentPath && (
              <div className="file-item" style={{ background: "var(--surface-highlight)", cursor: "pointer", padding: "12px", borderRadius: "8px", marginBottom: "8px" }} onClick={() => fetchFiles(parentPath)}>
                <div style={{ fontWeight: 600 }}>Previous Directory</div>
              </div>
            )}

            {!files.length && (
              <div style={{ textAlign: "center", padding: "60px 0", color: "var(--muted)" }}>
                <div style={{ opacity: 0.5, marginBottom: "16px" }}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
                  </svg>
                </div>
                Folder is empty
              </div>
            )}

            {files.map((f) => (
              <div key={f.path} className="file-item" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", borderBottom: "1px solid var(--border)" }}>
                {f.type === "dir" ? (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: "16px", flex: 1, cursor: "pointer" }} onClick={() => fetchFiles(f.path)}>
                      <div style={{ color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, color: "var(--text)" }}>{f.title || f.name}</div>
                        {f.is_gallery && <small style={{ color: "#eab308" }}>★ Gallery Album</small>}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <button className="action-btn" onClick={() => openMeta(f)} title="Edit Info">✎</button>
                      <button className="action-btn" onClick={() => toggleGallery(f.path, !f.is_gallery)} title="Toggle Gallery">
                        {f.is_gallery ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="#eab308" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                          </svg>
                        )}
                      </button>
                      <button className="action-btn danger" onClick={() => deleteItem(f.path)} title="Delete">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: "16px", overflow: "hidden" }}>
                      <div style={{
                        width: "48px", height: "48px", borderRadius: "8px", flexShrink: 0,
                        backgroundImage: getIcon(f.name) === "img" ? `url(${f.url})` : "none",
                        backgroundSize: "cover", backgroundPosition: "center",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        backgroundColor: "var(--surface-highlight)",
                      }}>
                        {getIcon(f.name) !== "img" && (
                          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
                          </svg>
                        )}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", color: "var(--text)" }}>{f.name}</div>
                        <div style={{ fontSize: "12px", color: "var(--muted)" }}>{f.size ? `${(f.size / 1024).toFixed(1)} KB` : ""}</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <a href={f.url} target="_blank" className="action-btn" title="Open">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                      </a>
                      <button className="action-btn" onClick={() => navigator.clipboard.writeText(window.location.origin + (f.url || "")).then(() => showToast("Link copied"))} title="Copy Link">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                      </button>
                      <button className="action-btn danger" onClick={() => deleteItem(f.path)} title="Delete">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {toast && (
        <div className="toast show" style={{ position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)", zIndex: 1000 }}>
          {toast}
        </div>
      )}
    </div>
  );
}
