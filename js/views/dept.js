// ==================== VIEW: DEPARTMENTS ====================
function renderDept(ct,cl){
  cl.innerHTML=`<button class="btn primary" onclick="openAdd()">+ Add Person</button>
    <button class="btn" onclick="openAddDept()" style="background:#1e293b;border-color:var(--ba);">+ Add Department</button>
    <button class="btn" onclick="eAll()">Expand All</button>
    <button class="btn" onclick="cAll()">Collapse All</button>
    <span style="flex:1"></span>
    <button class="btn" onclick="expJSON()">Export JSON</button>`;

  // VP + Leads at top
  const leads=data.filter(p=>p.type==='lead');
  let h=`<div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="card" style="border-color:var(--a);box-shadow:0 0 30px var(--ag);text-align:center;padding:16px 32px;">
      <span class="badge b-exec">VP of Training</span>
      <div class="name" style="margin-top:4px;">You</div>
      <div class="role-line">XGuard — MTL / QC / En ligne</div>
    </div></div>`;
  h+=`<div style="display:flex;justify-content:center;height:28px;"><div style="width:2px;height:100%;background:var(--ba);"></div></div>`;
  if(leads.length){
    h+=`<div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-bottom:8px;">`;
    leads.forEach(l=>{
      h+=`<div class="card" onclick="openEdit('${l.id}')" style="border-color:var(--g);box-shadow:0 0 12px rgba(52,211,153,0.08);text-align:center;min-width:200px;">
        <span class="badge b-lead">Lead</span>
        <span style="font-size:9px;color:var(--td);margin-left:5px;font-family:'Space Mono',monospace;text-transform:uppercase;letter-spacing:1px;">${DM[l.dept]?DM[l.dept].l:l.dept}</span>
        <div class="name" style="margin-top:3px;">${esc(l.name)}</div>
        <div class="role-line">${esc(l.role)}</div>
        <div style="font-size:10px;color:var(--g);margin-top:4px;">${getChildren(l.id).length} direct reports</div>
      </div>`;
    });
    h+=`</div>`;
    h+=`<div style="display:flex;justify-content:center;height:28px;"><div style="width:2px;height:100%;background:var(--ba);"></div></div>`;
  }

  // Departments
  h+=`<div class="dept-grid">`;
  departments.forEach(dept=>{
    const members=data.filter(p=>p.dept===dept.key&&p.type!=='lead');
    h+=`<div class="dept" id="dept-${dept.key}">
      <div class="dept-h" onclick="document.getElementById('dept-${dept.key}').classList.toggle('collapsed')">
        <div class="dept-dot" style="background:${dept.color};"></div><h3>${esc(dept.label)}</h3>
        <span class="cnt">${members.length}</span><span class="chev">▼</span>
        <button class="btn" style="margin-left:auto;font-size:10px;padding:2px 8px;" onclick="event.stopPropagation();editDept('${dept.key}')">✏️</button>
      </div>
      <div class="dept-body">${members.length?members.map(cardHTML).join(''):'<div class="empty">Empty</div>'}</div>
    </div>`;
  });
  h+=`</div>`;

  // ── Archived section (admin only) ──
  if (authIsAdmin()) {
    h += `<div style="margin-top:32px;border-top:1px solid var(--b);padding-top:20px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:12px;color:var(--td);font-weight:600;text-transform:uppercase;letter-spacing:1px;">🗃 Personnes archivées</span>
        <button class="btn" style="font-size:11px;padding:3px 10px;" onclick="toggleArchivedView()">
          ${_showArchived ? 'Masquer' : 'Afficher'}
        </button>
      </div>
      ${_showArchived ? _renderArchivedPeople() : ''}
    </div>`;
  }

  ct.innerHTML=h;
}

function _renderArchivedPeople() {
  if (!_archivedData.length) return '<div class="empty" style="color:var(--td);font-size:12px;">Aucune personne archivée.</div>';
  return `<div style="display:flex;flex-wrap:wrap;gap:10px;">` +
    _archivedData.map(p => `
      <div class="card" style="opacity:0.65;border-style:dashed;min-width:180px;">
        <span class="badge" style="background:rgba(139,138,135,0.2);color:var(--td);">Archivé</span>
        <div class="name" style="margin-top:3px;">${esc(p.name)}</div>
        <div class="role-line">${esc(p.role)}</div>
        <div style="margin-top:8px;">
          <button class="btn" style="font-size:10px;padding:3px 10px;" onclick="restoreP('${esc(p.id)}')">↩ Restaurer</button>
        </div>
      </div>`).join('') +
    `</div>`;
}

async function toggleArchivedView() {
  _showArchived = !_showArchived;
  if (_showArchived) {
    try {
      _archivedData = await dbGetArchivedPeople();
    } catch(e) {
      _archivedData = [];
      console.error('Failed to load archived:', e);
    }
  }
  render();
}

async function restoreP(id) {
  if (!confirm('Restaurer cette personne?')) return;
  await dbRestorePerson(id);
  _archivedData = _archivedData.filter(p => p.id !== id);
  // Reload active people
  await loadFromSupabase();
  render();
}

function eAll(){document.querySelectorAll('.dept').forEach(d=>d.classList.remove('collapsed'));}
function cAll(){document.querySelectorAll('.dept').forEach(d=>d.classList.add('collapsed'));}
