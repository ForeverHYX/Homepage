import os
import shutil
from pathlib import Path
from typing import List, Any

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse

from app.config import (
    TEMPLATE_BASE, STYLES, UPLOAD_DIR,
    ICON_UPLOAD_CLOUD, ICON_FILE, ICON_OPEN, ICON_TRASH, ICON_COPY, 
    ICON_FOLDER, ICON_STAR, ICON_STAR_FILLED
)
from app.utils import (
    safe_join, process_uploaded_image, get_folder_meta, save_folder_meta,
    get_gallery_folders, toggle_gallery_folder
)
from app.auth import require_login, get_current_user

router = APIRouter()

@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request) -> Any:
    if not get_current_user(request):
        return RedirectResponse("/login")

    content = f"""
    <div class="container upload-grid">
      <section>
        <div style="background:var(--surface); padding:24px; border-radius:12px; border:1px solid var(--border); position:sticky; top:100px;">
          <h2 style="margin-top:0; font-size:18px;">Upload Manager</h2>
          
          <div style="margin-bottom:16px;">
             <div style="font-weight:600; margin-bottom:8px; font-size:14px; color:var(--muted);">Current Path:</div>
             <div style="display:flex; gap:8px; align-items:center; background:var(--surface-highlight); padding:8px; border-radius:6px; font-family:monospace; overflow-x:auto;">
                 <button class="action-btn" onclick="openPath('')">Home</button>
                 <span id="currentPathDisplay">/</span>
             </div>
          </div>

          <div style="display:flex; gap:8px; margin-bottom:16px;">
             <input type="text" id="folderName" placeholder="New Folder" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
             <button class="btn btn-primary" id="createFolderBtn" style="padding:0 12px;">+</button>
          </div>

          <div id="drop" class="drop-zone">
            <div style="color:var(--primary); margin-bottom:12px;">{ICON_UPLOAD_CLOUD}</div>
            <p style="margin:0; font-weight:600; color:var(--text); font-size:15px;">Click to Add Files</p>
            <input id="fileInput" type="file" multiple />
          </div>
          <div id="queue-status" style="margin-top:16px; font-size:14px; text-align:center; color:var(--muted);"></div>
          <button id="uploadBtn" class="btn btn-primary" style="margin-top:16px;" disabled>Start Upload</button>
        </div>
      </section>
      
      <section>
        <div style="background:var(--surface); padding:32px; border-radius:12px; border:1px solid var(--border); min-height:400px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
            <h2 style="margin:0; font-size:20px;">Files & Folders</h2>
            <button id="refreshBtn" onclick="fetchFiles(currentPath)" class="action-btn">Refresh</button>
          </div>
          <div id="fileList"></div>
          <div id="emptyState" style="text-align:center; padding:60px 0; color:var(--muted); display:none;">
            <div style="opacity:0.5; margin-bottom:16px;">{ICON_FILE}</div>
            Folder is empty
          </div>
        </div>
      </section>
    </div>
    <div id="toast" class="toast">Action Completed</div>
    
    <!-- Edit Meta Modal -->
    <div id="metaModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; align-items:center; justify-content:center;">
        <div style="background:var(--surface); padding:24px; border-radius:12px; width:100%; max-width:400px; box-shadow:var(--shadow);">
            <h3 style="margin:0 0 16px;">Edit Folder Info</h3>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Title</label>
                <input id="metaTitle" type="text" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Shoot Date</label>
                <input id="metaDate" type="date" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Author</label>
                <input id="metaAuthor" type="text" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);" placeholder="Yixun Hong">
            </div>
            <div style="margin-bottom:20px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Description</label>
                <textarea id="metaDesc" rows="3" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text); font-family:inherit;"></textarea>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="btn" style="background:var(--surface-highlight); color:var(--text);" onclick="closeMetaModal()">Cancel</button>
                <button class="btn btn-primary" style="width:auto;" onclick="saveMeta()">Save</button>
            </div>
        </div>
    </div>
    """

    script = f"""
      const drop = document.getElementById('drop');
      const fileInput = document.getElementById('fileInput');
      const uploadBtn = document.getElementById('uploadBtn');
      const queueEl = document.getElementById('queue-status');
      const fileList = document.getElementById('fileList');
      const toast = document.getElementById('toast');
      const pathDisplay = document.getElementById('currentPathDisplay');
      
      const metaModal = document.getElementById('metaModal');
      const metaTitle = document.getElementById('metaTitle');
      const metaDesc = document.getElementById('metaDesc');
      const metaDate = document.getElementById('metaDate');
      const metaAuthor = document.getElementById('metaAuthor');
      let currentEditPath = "";
      
      let queue = [];
      let currentPath = "";

      function getIcon(filename) {{
        const ext = filename.split('.').pop().toLowerCase();
        if (['jpg','jpeg','png','gif','webp'].includes(ext)) return 'img';
        return 'file';
      }}

      function showToast(msg) {{
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
      }}
      
      window.openMetaModal = (path, title, desc, date, author) => {{
          currentEditPath = path;
          metaTitle.value = title || "";
          metaDesc.value = desc || "";
          metaDate.value = date || "";
          metaAuthor.value = author || "Yixun Hong";
          metaModal.style.display = 'flex';
      }};
      
      window.closeMetaModal = () => {{
          metaModal.style.display = 'none';
      }};
      
      window.saveMeta = async () => {{
          const form = new FormData();
          form.append('path', currentEditPath);
          form.append('title', metaTitle.value);
          form.append('description', metaDesc.value);
          form.append('date', metaDate.value);
          form.append('author', metaAuthor.value);
          
          try {{
            await fetch('/api/folder/meta', {{ method: 'POST', body: form }});
            closeMetaModal();
            fetchFiles(currentPath);
            showToast('Info Updated');
          }} catch(e) {{ alert(e); }}
      }};

      function updateQueue(files) {{
        queue = [...queue, ...files];
        uploadBtn.disabled = queue.length === 0;
        queueEl.textContent = queue.length ? `${{queue.length}} file(s) ready` : '';
      }}

      drop.addEventListener('dragover', (e) => {{ e.preventDefault(); drop.classList.add('drag'); }});
      drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
      drop.addEventListener('drop', (e) => {{
        e.preventDefault();
        drop.classList.remove('drag');
        updateQueue([...e.dataTransfer.files]);
      }});
      fileInput.addEventListener('change', (e) => updateQueue([...e.target.files]));

      async function fetchFiles(path = currentPath) {{
         // Fix: Ensure path is a string, not an Event object
         if (typeof path !== 'string') path = currentPath;

         currentPath = path;
         pathDisplay.textContent = path ? '/ ' + path : '/';
         
         const res = await fetch(`/api/files?path=${{encodeURIComponent(path)}}`);
         if (res.status === 401) return location.href = '/login';
         const data = await res.json();
         
         fileList.innerHTML = '';
         if (path) {{
            const parts = path.split('/');
            parts.pop();
            const upPath = parts.join('/');
            const div = document.createElement('div');
            div.className = 'file-item';
            div.style.background = 'var(--surface-highlight)';
            div.innerHTML = `<div style="cursor:pointer; width:100%; display:flex; gap:12px; font-weight:600;" onclick="openPath('${{upPath}}')">Previous Directory</div>`;
            fileList.appendChild(div);
         }}

         if (data.files.length === 0) {{
           document.getElementById('emptyState').style.display = 'block';
         }} else {{
           document.getElementById('emptyState').style.display = 'none';
         }}

         data.files.forEach(f => {{
           const div = document.createElement('div');
           div.className = 'file-item';
           
           if (f.type === 'dir') {{
               const isGal = f.is_gallery;
               // Escaping for JS string safety
               const safeTitle = (f.title || f.name).replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, ' ');
               const safeDesc = (f.description || "").replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, '\\n');
               const safeDate = (f.date || "");
               const safeAuthor = (f.author || "Yixun Hong").replace(/'/g, "\\'").replace(/"/g, '&quot;');
               const safePath = f.path.replace(/'/g, "\\'");
               
               div.innerHTML = `
                 <div style="display:flex; align-items:center; gap:16px; flex:1; cursor:pointer;" onclick="openPath('${{safePath}}')">
                   <div class="file-preview" style="background:var(--surface-highlight); color:var(--primary); display:flex; align-items:center; justify-content:center;">{ICON_FOLDER}</div>
                   <div>
                       <div style="font-weight:600;">${{f.title || f.name}}</div>
                       ${{isGal ? '<small style="color:#eab308">★ Gallery Album</small>' : ''}}
                   </div>
                 </div>
                 <div style="display:flex; gap:4px; align-items:center;">
                    <button class="action-btn" onclick="openMetaModal('${{safePath}}', '${{safeTitle}}', '${{safeDesc}}', '${{safeDate}}', '${{safeAuthor}}')" title="Edit Info">✎</button>
                    <button class="action-btn" onclick="toggleGallery('${{safePath}}', ${{!isGal}})" title="Toggle Gallery">
                        ${{isGal ? `{ICON_STAR_FILLED}` : `{ICON_STAR}`}}
                    </button>
                    <button class="action-btn danger" onclick="deleteFile('${{f.path}}')" title="Delete">{ICON_TRASH}</button>
                 </div>
               `;
           }} else {{
               const isImg = getIcon(f.name) === 'img';
               const bg = isImg ? `url(${{f.url}})` : 'none';
               const iconHtml = isImg ? '' : `{ICON_FILE}`;
               
               div.innerHTML = `
                 <div style="display:flex; align-items:center; gap:16px; overflow:hidden;">
                   <div class="file-preview" style="background-image:${{bg}}; background-size:cover; background-position:center;">
                     ${{iconHtml}}
                   </div>
                   <div style="min-width:0;">
                     <div style="font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${{f.name}}</div>
                     <div style="font-size:12px; color:var(--muted);">${{(f.size/1024).toFixed(1)}} KB</div>
                   </div>
                 </div>
                 <div style="display:flex; gap:4px;">
                    <a href="${{f.url}}" target="_blank" class="action-btn" title="Open">{ICON_OPEN}</a>
                    <button class="action-btn" onclick="copyUrl('${{f.url}}')" title="Copy Link">{ICON_COPY}</button>
                    <button class="action-btn danger" onclick="deleteFile('${{f.url.replace('/uploads/', '')}}')" title="Delete">{ICON_TRASH}</button>
                 </div>
               `;
           }}
           fileList.appendChild(div);
         }});
      }}

      window.openPath = (path) => fetchFiles(path);

      window.toggleGallery = async (path, enable) => {{
          const form = new FormData();
          form.append('path', path);
          form.append('enable', enable);
          try {{
            await fetch('/api/gallery/toggle', {{method:'POST', body:form}});
            fetchFiles(currentPath);
            showToast('Gallery Updated');
          }} catch(e) {{ alert(e); }}
      }};

      document.getElementById('createFolderBtn').addEventListener('click', async () => {{
          const name = document.getElementById('folderName').value;
          if (!name) return;
          const form = new FormData();
          form.append('name', name);
          form.append('path', currentPath);
          await fetch('/api/folder', {{method:'POST', body:form}});
          document.getElementById('folderName').value = '';
          fetchFiles(currentPath);
      }});

      window.copyUrl = async (url) => {{
        await navigator.clipboard.writeText(location.origin + url);
        showToast('Link copied');
      }};

      window.deleteFile = async (path) => {{
        if (!confirm('Permanently delete ' + path + '? Folder contents will be lost.')) return;
        const res = await fetch(`/api/files/${{encodeURIComponent(path)}}`, {{ method:'DELETE' }});
        if (res.ok) {{ showToast('Deleted'); fetchFiles(currentPath); }}
      }};


      uploadBtn.addEventListener('click', async () => {{
        if (queue.length === 0) return;
        
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        
        try {{
            for (const f of queue) {{
              const form = new FormData();
              form.append('file', f);
              form.append('path', currentPath);
              
              const res = await fetch('/api/upload', {{ method:'POST', body:form }});
              if (!res.ok) {{
                  const txt = await res.text();
                  console.error('Upload failed', res.status, txt);
                  alert(`Upload failed: ${{res.status}}`);
              }}
            }}
            showToast('Upload Complete');
        }} catch(e) {{
            alert(`Network error: ${{e}}`);
        }} finally {{
            queue = [];
            uploadBtn.textContent = 'Start Upload';
            queueEl.textContent = '';
            fetchFiles(currentPath);
        }}
      }});

      // Remove default event listener in favor of onclick with correct arg
      // document.getElementById('refreshBtn').addEventListener('click', fetchFiles);
      fetchFiles();
    """
    return TEMPLATE_BASE.format(title="Upload | Yixun Hong", styles=STYLES, content=content, script=script)


@router.post("/api/upload")
async def upload_file_api(request: Request, file: UploadFile = File(...), path: str = Form("")) -> JSONResponse:
    require_login(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    
    # Resolve path
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
        if not target_dir.exists():
             target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    target_path = safe_join(target_dir, safe_name)

    with target_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024 * 5) # 5MB chunks
            if not chunk:
                break
            f.write(chunk)

    # Process Image (JPG -> WebP)
    final_name = process_uploaded_image(target_path)
    
    # Return relative URL
    rel_path = target_path.parent.relative_to(UPLOAD_DIR)
    if str(rel_path) == ".":
        url = f"/uploads/{final_name}"
    else:
        url = f"/uploads/{rel_path}/{final_name}"

    return JSONResponse({"filename": final_name, "url": url})


@router.post("/api/folder")
def create_folder_api(request: Request, name: str = Form(...), path: str = Form("")) -> JSONResponse:
    require_login(request)
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
    
    final_path = safe_join(target_dir, name)
    try:
        final_path.mkdir(exist_ok=True)
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"detail": "Created"})


@router.post("/api/folder/meta")
def update_folder_meta(request: Request, path: str = Form(...), title: str = Form(...), description: str = Form(...), date: str = Form(""), author: str = Form("Yixun Hong")) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")
    
    save_folder_meta(target, title, description, date, author)
    return JSONResponse({"detail": "Updated"})


@router.post("/api/gallery/toggle")
def toggle_gallery_api(request: Request, path: str = Form(...), enable: bool = Form(...)) -> JSONResponse:
    require_login(request)
    # Validate path exists
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")
    
    # Store relative path by normalized string
    rel_path = str(target.relative_to(UPLOAD_DIR))
    toggle_gallery_folder(rel_path, enable)
    return JSONResponse({"detail": "Updated"})


@router.get("/api/files")
def list_files_api(request: Request, path: str = "") -> JSONResponse:
    require_login(request)
    
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
    
    if not target_dir.exists():
         raise HTTPException(status_code=404, detail="Path not found")

    items: List[dict] = []
    gallery_set = set(get_gallery_folders())
    
    # Sort: Folders first, then files (by mtime desc)
    try:
        entries = list(target_dir.iterdir())
    except NotADirectoryError:
         raise HTTPException(status_code=400, detail="Not a directory")

    entries.sort(key=lambda x: (not x.is_dir(), -x.stat().st_mtime))
    
    for p in entries:
        rel_path = str(p.relative_to(UPLOAD_DIR))
        
        if p.is_dir():
            meta = get_folder_meta(p)
            items.append({
                "name": p.name,
                "type": "dir",
                "is_gallery": rel_path in gallery_set,
                "path": rel_path,
                "title": meta.get("title", p.name),
                "description": meta.get("description", ""),
                "date": meta.get("date", ""),
                "author": meta.get("author", "Yixun Hong")
            })
        else:
            items.append({
                "name": p.name,
                "type": "file",
                "size": p.stat().st_size,
                "url": f"/uploads/{rel_path}"
            })
            
    return JSONResponse({"files": items, "current_path": path})


@router.delete("/api/files/{path:path}")
def delete_file_api(request: Request, path: str) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if target.is_dir():
         shutil.rmtree(target)
    else:
         os.remove(target)
    return JSONResponse({"detail": "Deleted"})


@router.get("/api/files/{file_path:path}")
def download_file_api(file_path: str) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
