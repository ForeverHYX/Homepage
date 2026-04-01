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

      function getIcon(filename) {
        if (!filename) return 'file';
        const parts = filename.split('.');
        if (parts.length < 2) return 'file';
        const ext = parts.pop().toLowerCase();
        if (['jpg','jpeg','png','gif','webp'].includes(ext)) return 'img';
        return 'file';
      }

      function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
      }
      
      window.openMetaModal = (path, title, desc, date, author) => {
          currentEditPath = path;
          metaTitle.value = title || "";
          metaDesc.value = desc || "";
          metaDate.value = date || "";
          metaAuthor.value = author || "Yixun Hong";
          metaModal.style.display = 'flex';
      };
      
      window.closeMetaModal = () => {
          metaModal.style.display = 'none';
      };
      
      window.saveMeta = async () => {
          const form = new FormData();
          form.append('path', currentEditPath);
          form.append('title', metaTitle.value);
          form.append('description', metaDesc.value);
          form.append('date', metaDate.value);
          form.append('author', metaAuthor.value);
          
          try {
            await fetch('/api/folder/meta', { method: 'POST', body: form });
            closeMetaModal();
            fetchFiles(currentPath);
            showToast('Info Updated');
          } catch(e) { alert(e); }
      };

      function updateQueue(files) {
        queue = [...queue, ...files];
        uploadBtn.disabled = queue.length === 0;
        queueEl.textContent = queue.length ? `${queue.length} file(s) ready` : '';
      }

      drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
      drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
      drop.addEventListener('drop', (e) => {
        e.preventDefault();
        drop.classList.remove('drag');
        updateQueue([...e.dataTransfer.files]);
      });
      fileInput.addEventListener('change', (e) => updateQueue([...e.target.files]));

      async function fetchFiles(path = currentPath) {
         // Fix: Ensure path is a string, not an Event object
         if (typeof path !== 'string') path = currentPath;

         currentPath = path;
         pathDisplay.textContent = path ? '/ ' + path : '/';
         
         try {
             const res = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
             if (res.status === 401) return location.href = '/login';
             if (!res.ok) throw new Error(res.statusText);
             const data = await res.json();
             
             fileList.innerHTML = '';
             if (path) {
                const parts = path.split('/');
                parts.pop();
                const upPath = parts.join('/');
                const safeUpPath = upPath.replace(/'/g, "\\'");
                const div = document.createElement('div');
                div.className = 'file-item';
                div.style.background = 'var(--surface-highlight)';
                div.innerHTML = `<div style="cursor:pointer; width:100%; display:flex; gap:12px; font-weight:600;" onclick="openPath('${safeUpPath}')">Previous Directory</div>`;
                fileList.appendChild(div);
             }

             if (!data.files || data.files.length === 0) {
               document.getElementById('emptyState').style.display = 'block';
             } else {
               document.getElementById('emptyState').style.display = 'none';
             }

             if (data.files) {
                 data.files.forEach(f => {
                   try {
                       const div = document.createElement('div');
                       div.className = 'file-item';
                       
                       if (f.type === 'dir') {
                           const isGal = f.is_gallery;
                           // Escaping for JS string safety
                           const safeTitle = (f.title || f.name).replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\\n/g, ' ');
                           const safeDesc = (f.description || "").replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\\n/g, '\\\\n');
                           const safeDate = (f.date || "");
                           const safeAuthor = (f.author || "Yixun Hong").replace(/'/g, "\\'").replace(/"/g, '&quot;');
                           const safePath = f.path.replace(/'/g, "\\'");
                           
                           div.innerHTML = `
                             <div style="display:flex; align-items:center; gap:16px; flex:1; cursor:pointer;" onclick="openPath('${safePath}')">
                               <div class="file-preview" style="background:var(--surface-highlight); color:var(--primary); display:flex; align-items:center; justify-content:center;">{ICON_FOLDER}</div>
                               <div>
                                   <div style="font-weight:600;">${f.title || f.name}</div>
                                   ${isGal ? '<small style="color:#eab308">★ Gallery Album</small>' : ''}
                               </div>
                             </div>
                             <div style="display:flex; gap:4px; align-items:center;">
                                <button class="action-btn" onclick="openMetaModal('${safePath}', '${safeTitle}', '${safeDesc}', '${safeDate}', '${safeAuthor}')" title="Edit Info">✎</button>
                                <button class="action-btn" onclick="toggleGallery('${safePath}', ${!isGal})" title="Toggle Gallery">
                                    ${isGal ? `{ICON_STAR_FILLED}` : `{ICON_STAR}`}
                                </button>
                                <button class="action-btn danger" onclick="deleteFile('${safePath}')" title="Delete">{ICON_TRASH}</button>
                             </div>
                           `;
                       } else {
                           const isImg = getIcon(f.name) === 'img';
                           const encodedUrl = encodeURI(f.url).replace(/'/g, '%27');
                           const bg = isImg ? `url('${encodedUrl}')` : 'none';
                           const iconHtml = isImg ? '' : `{ICON_FILE}`;
                           const safeUrl = f.url.replace(/'/g, "\\'");
                           
                           div.innerHTML = `
                             <div style="display:flex; align-items:center; gap:16px; overflow:hidden;">
                               <div class="file-preview" style="background-image:${bg}; background-size:cover; background-position:center;">
                                 ${iconHtml}
                               </div>
                               <div style="min-width:0;">
                                 <div style="font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${f.name}</div>
                                 <div style="font-size:12px; color:var(--muted);">${(f.size/1024).toFixed(1)} KB</div>
                               </div>
                             </div>
                             <div style="display:flex; gap:4px;">
                                <a href="${f.url}" target="_blank" class="action-btn" title="Open">{ICON_OPEN}</a>
                                <button class="action-btn" onclick="copyUrl('${safeUrl}')" title="Copy Link">{ICON_COPY}</button>
                                <button class="action-btn danger" onclick="deleteFile('${safeUrl.replace('/uploads/', '')}')" title="Delete">{ICON_TRASH}</button>
                             </div>
                           `;
                       }
                       fileList.appendChild(div);
                   } catch (err) {
                       console.error(err);
                   }
                 });
             }
         } catch(e) {
             console.error(e);
             fileList.innerHTML = `<div style="padding:20px; text-align:center; color:red">Error: ${e.message}</div>`;
         }
      }

      window.openPath = (path) => fetchFiles(path);

      window.toggleGallery = async (path, enable) => {
          const form = new FormData();
          form.append('path', path);
          form.append('enable', enable);
          try {
            await fetch('/api/gallery/toggle', {method:'POST', body:form});
            fetchFiles(currentPath);
            showToast('Gallery Updated');
          } catch(e) { alert(e); }
      };

      document.getElementById('createFolderBtn').addEventListener('click', async () => {
          const name = document.getElementById('folderName').value;
          if (!name) return;
          const form = new FormData();
          form.append('name', name);
          form.append('path', currentPath);
          await fetch('/api/folder', {method:'POST', body:form});
          document.getElementById('folderName').value = '';
          fetchFiles(currentPath);
      });

      window.copyUrl = async (url) => {
        await navigator.clipboard.writeText(location.origin + url);
        showToast('Link copied');
      };

      window.deleteFile = async (path) => {
        if (!confirm('Permanently delete ' + path + '? Folder contents will be lost.')) return;
        const res = await fetch(`/api/files/${encodeURIComponent(path)}`, { method:'DELETE' });
        if (res.ok) { showToast('Deleted'); fetchFiles(currentPath); }
      };


      uploadBtn.addEventListener('click', async () => {
        if (queue.length === 0) return;
        
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        
        try {
            for (const f of queue) {
              const form = new FormData();
              form.append('file', f);
              form.append('path', currentPath);
              
              const res = await fetch('/api/upload', { method:'POST', body:form });
              if (!res.ok) {
                  const txt = await res.text();
                  console.error('Upload failed', res.status, txt);
                  alert(`Upload failed: ${res.status}`);
              }
            }
            showToast('Upload Complete');
        } catch(e) {
            alert(`Network error: ${e}`);
        } finally {
            queue = [];
            uploadBtn.textContent = 'Start Upload';
            queueEl.textContent = '';
            fetchFiles(currentPath);
        }
      });

      // Remove default event listener in favor of onclick with correct arg
      // document.getElementById('refreshBtn').addEventListener('click', fetchFiles);
      fetchFiles();