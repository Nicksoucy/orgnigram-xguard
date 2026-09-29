// ==================== XGUARD CARD KIT (portable, offline) ====================
// Standalone shell around the org chart's card renderer (app/cards.js, copied
// from js/views/cards.js by build.sh). It provides the same globals the org
// chart app provides (data, departments, esc, initials, …) but keeps people
// in this computer's localStorage instead of Supabase.

const KIT_MODE = true;                 // tells cards.js to hide app-only buttons
const KIT_STORE = 'xgKitPeople';

let data = [];                         // people (same shape as the org chart app)
let departments = [];                  // [{key,label,color}]
let VP = null;                         // unused in the kit; kept for cards.js compatibility
let _kitView = 'people';
let _kitEditId = null;

const KIT_PALETTE = ['#60a5fa','#34d399','#a78bfa','#f472b6','#fbbf24','#22d3ee','#f87171','#86efac','#fdba74','#ff6b35'];

// ---- Helpers mirrored from the org chart's js/utils.js ----
const DM = new Proxy({}, { get: (_, k) => { const d = departments.find(x => x.key === k); return d ? { l: d.label, d: d.color } : null; } });
function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
function avatarColor(id) { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) & 0xffff; return KIT_PALETTE[h % KIT_PALETTE.length]; }
function initials(name) { const p = (name || '').trim().split(/\s+/); return ((p[0]?.[0] || '') + (p[1]?.[0] || '')).toUpperCase(); }
function bl(t) { return t === 'lead' ? 'Lead' : t === 'employee' ? 'Employee' : t === 'exec' ? 'VP' : 'Contractor'; }
function allPeople() { return data; }
function gid() { return 'p_' + Math.random().toString(36).substr(2, 9); }
function showFlash(msg, isDanger) {
  const el = document.createElement('div');
  el.className = 'hor-flash' + (isDanger ? ' danger' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 400); }, 2800);
}

// ---- Persistence ----
function kitLoad() {
  try {
    const s = JSON.parse(localStorage.getItem(KIT_STORE) || 'null');
    if (s) { data = s.people || []; departments = s.departments || []; }
  } catch (e) { console.warn('kit load failed', e); }
}
function kitSave() {
  try { localStorage.setItem(KIT_STORE, JSON.stringify({ people: data, departments })); }
  catch (e) { showFlash('Impossible de sauvegarder sur cet ordinateur.', true); }
}

function kitSlug(s) {
  return (s || '').toString().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'autre';
}
// Find or create a department by label (or key). Returns its key, '' if blank.
function kitEnsureDept(labelOrKey) {
  const v = (labelOrKey || '').trim();
  if (!v) return '';
  const hit = departments.find(d => d.key === v || d.label.toLowerCase() === v.toLowerCase());
  if (hit) return hit.key;
  const key = kitSlug(v);
  if (!departments.some(d => d.key === key)) {
    departments.push({ key, label: v, color: KIT_PALETTE[departments.length % KIT_PALETTE.length] });
  }
  return key;
}
function kitNormType(t) {
  const v = kitSlug(t);
  if (['lead', 'chef', 'chef_equipe', 'superviseur', 'responsable'].includes(v)) return 'lead';
  if (['vp', 'exec', 'direction', 'directeur', 'directrice', 'president'].includes(v)) return 'exec';
  if (['contractor', 'contractuel', 'contractuelle', 'contracteur', 'pigiste', 'sous_traitant'].includes(v)) return 'contractor';
  return 'employee';
}
function kitSplitPrograms(v) {
  if (Array.isArray(v)) return v.filter(Boolean);
  return (v || '').toString().split(/[;,|/]/).map(s => s.trim()).filter(Boolean);
}

// ==================== VIEWS ====================
function kitSwitch(v, btn) {
  _kitView = v;
  document.querySelectorAll('.vtab').forEach(b => b.classList.toggle('active', b === btn || b.dataset.view === v));
  render();
}
function render() {
  const ct = document.getElementById('content'), cl = document.getElementById('controls');
  document.getElementById('hdrSub').textContent =
    `${data.length} personne(s) · fonctionne hors ligne · données gardées sur cet ordinateur`;
  if (_kitView === 'cards') renderCards(ct, cl);
  else if (_kitView === 'help') kitRenderHelp(ct, cl);
  else kitRenderPeople(ct, cl);
}

function kitRenderPeople(ct, cl) {
  cl.innerHTML = `
    <button class="btn primary" onclick="document.getElementById('kitFile').click()">📥 Importer (JSON / Excel / CSV)</button>
    <button class="btn" onclick="kitExportCSV()">📤 Exporter CSV</button>
    <button class="btn" onclick="kitDownloadTemplate()">📄 Modèle Excel</button>
    <span style="flex:1"></span>
    ${data.length ? `<button class="btn danger" onclick="kitClearAll()">Tout effacer</button>` : ''}`;

  const p = _kitEditId ? data.find(x => x.id === _kitEditId) : null;
  const deptLabel = p && DM[p.dept] ? DM[p.dept].l : '';
  const typeOpt = (v, l) => `<option value="${v}"${(p ? p.type : 'employee') === v ? ' selected' : ''}>${l}</option>`;
  let h = `
    <div class="kit-form">
      <div class="f wide"><label>Nom complet</label><input id="kName" value="${esc(p ? p.name : '')}" placeholder="ex. Marie Tremblay"></div>
      <div class="f wide"><label>Titre / rôle</label><input id="kRole" value="${esc(p ? p.role : '')}" placeholder="ex. Formatrice BSP"></div>
      <div class="f"><label>Type</label><select id="kType">${typeOpt('employee', 'Employé')}${typeOpt('contractor', 'Contractuel')}${typeOpt('lead', 'Lead')}${typeOpt('exec', 'Direction / VP')}</select></div>
      <div class="f"><label>Département</label><input id="kDept" list="kDeptList" value="${esc(deptLabel)}" placeholder="ex. Formation">
        <datalist id="kDeptList">${departments.map(d => `<option value="${esc(d.label)}">`).join('')}</datalist></div>
      <div class="f wide"><label>Programmes (séparés par ;)</label><input id="kProg" value="${esc(p ? (p.programs || []).join('; ') : '')}" placeholder="ex. BSP; RCR; Drone"></div>
      <div class="f actions">
        <button class="btn primary" onclick="kitSavePerson()">${p ? 'Enregistrer' : '+ Ajouter'}</button>
        ${p ? `<button class="btn" onclick="kitCancelEdit()">Annuler</button>` : ''}
      </div>
    </div>`;

  if (!data.length) {
    h += `<div class="kit-empty">Aucune personne pour l'instant.<br>
      Ajoutez-en avec le formulaire ci-dessus, ou <b>📥 Importer</b> :<br>
      • le fichier <code>xguard-cartes-personnes-….json</code> exporté de l'organigramme (onglet Cartes → 📦 Exporter pour le kit)<br>
      • un fichier Excel / CSV (colonnes : nom, role, type, departement, programmes — voir 📄 Modèle Excel)</div>`;
  } else {
    h += `<table class="kit-table"><thead><tr><th>Nom</th><th>Rôle</th><th>Type</th><th>Département</th><th>Programmes</th><th></th></tr></thead><tbody>`;
    data.forEach(x => {
      const d = departments.find(dd => dd.key === x.dept);
      h += `<tr>
        <td><span class="av" style="background:${x.avatarColor || avatarColor(x.id)}">${esc(initials(x.name))}</span>${esc(x.name)}</td>
        <td class="muted">${esc(x.role)}</td>
        <td class="muted">${esc(bl(x.type))}</td>
        <td>${d ? `<span class="dot" style="background:${d.color}"></span>${esc(d.label)}` : '<span class="muted">—</span>'}</td>
        <td class="muted">${esc((x.programs || []).join(', '))}</td>
        <td style="text-align:right;white-space:nowrap;">
          <button class="btn small" onclick="kitEdit('${x.id}')">✏️</button>
          <button class="btn small danger" onclick="kitDelete('${x.id}')">🗑</button>
        </td></tr>`;
    });
    h += `</tbody></table>`;
  }
  ct.innerHTML = h;
}

function kitRenderHelp(ct, cl) {
  cl.innerHTML = '';
  ct.innerHTML = `<div class="kit-help">
    <h2>1. Mettre les personnes dans le kit</h2>
    <ol>
      <li><b>Depuis l'organigramme</b> : onglet <b>Cartes</b> → <b>📦 Exporter pour le kit</b>. Ici : <b>Personnes → 📥 Importer</b> ce fichier <code>.json</code>. Les options de carte suivent aussi.</li>
      <li><b>Depuis Excel</b> : <b>📄 Modèle Excel</b>, remplir, puis <b>📥 Importer</b>. Colonnes : <code>nom</code>, <code>role</code>, <code>type</code> (employé / contractuel / lead / vp), <code>departement</code>, <code>programmes</code> (séparés par <code>;</code>), <code>id</code> (facultatif).</li>
      <li><b>À la main</b> : le formulaire en haut de l'onglet Personnes.</li>
    </ol>
    <p>Un import <b>met à jour</b> les personnes existantes (même id, ou même nom) et ajoute les nouvelles.</p>
    <h2>2. Imprimer</h2>
    <ol>
      <li>Onglet <b>Cartes</b> → cocher les personnes → vérifier l'aperçu (taille réelle).</li>
      <li><b>🖨 Imprimer</b> → imprimante <b>HiTi</b> → <b>Échelle 100 %</b>, <b>Marges : aucune</b>, en-têtes/pieds <b>décochés</b>.</li>
      <li>Ou <b>📄 Export PDF</b> puis imprimer le PDF en <b>taille réelle</b>.</li>
    </ol>
    <h2>3. Liseré blanc, carte décalée ?</h2>
    <ul>
      <li>Pilote HiTi → activer <b>Over-the-edge</b> (impression bord à bord), et/ou <b>⚙️ Options carte → Fond perdu 1 mm</b>.</li>
      <li>Carte décalée : pilote HiTi → <b>Position adjustment</b>.</li>
      <li>Carte trop petite : l'échelle n'est pas à 100 % (décocher « Ajuster à la page »).</li>
    </ul>
    <p>Le guide complet (installation du pilote, ruban YMCKO, calibration) est dans <code>GUIDE-HITI.md</code> à côté de ce fichier.</p>
    <h2>Où sont mes données ?</h2>
    <p>Dans le navigateur de <b>cet ordinateur</b> uniquement (rien n'est envoyé sur internet). Pour sauvegarder ou changer d'ordinateur : <b>📤 Exporter CSV</b>, puis réimporter ailleurs.</p>
  </div>`;
}

// ==================== PEOPLE ACTIONS ====================
function kitSavePerson() {
  const name = document.getElementById('kName').value.trim();
  if (!name) { showFlash('Le nom est obligatoire.', true); return; }
  const fields = {
    name,
    role: document.getElementById('kRole').value.trim(),
    type: document.getElementById('kType').value,
    dept: kitEnsureDept(document.getElementById('kDept').value),
    programs: kitSplitPrograms(document.getElementById('kProg').value),
  };
  if (_kitEditId) {
    Object.assign(data.find(x => x.id === _kitEditId), fields);
    showFlash('Personne mise à jour.');
  } else {
    const id = gid();
    data.push(Object.assign({ id, avatarColor: avatarColor(id) }, fields));
    showFlash('Personne ajoutée.');
  }
  _kitEditId = null;
  kitPruneDepts(); kitSave(); render();
}
function kitEdit(id) { _kitEditId = id; render(); window.scrollTo(0, 0); }
function kitCancelEdit() { _kitEditId = null; render(); }
function kitDelete(id) {
  const p = data.find(x => x.id === id);
  if (!p || !confirm(`Supprimer ${p.name} ?`)) return;
  data = data.filter(x => x.id !== id);
  _cardSel.delete(id);
  if (_kitEditId === id) _kitEditId = null;
  kitPruneDepts(); kitSave(); render();
}
function kitClearAll() {
  if (!confirm('Effacer toutes les personnes de ce kit ? (Pensez à 📤 Exporter CSV avant.)')) return;
  data = []; departments = []; _cardSel.clear(); _kitEditId = null;
  kitSave(); render();
}
// Drop departments no one belongs to any more.
function kitPruneDepts() { departments = departments.filter(d => data.some(p => p.dept === d.key)); }

// ==================== IMPORT / EXPORT ====================
function kitImportFile(file) {
  if (!file) return;
  const name = file.name.toLowerCase();
  const reader = new FileReader();
  reader.onerror = () => showFlash('Lecture du fichier impossible.', true);
  if (name.endsWith('.json')) {
    reader.onload = () => {
      try { kitImportJSON(JSON.parse(reader.result)); }
      catch (e) { console.error(e); showFlash('JSON invalide.', true); }
    };
    reader.readAsText(file);
  } else if (name.endsWith('.csv') || name.endsWith('.xlsx') || name.endsWith('.xls')) {
    reader.onload = () => {
      try {
        const wb = XLSX.read(new Uint8Array(reader.result), { type: 'array' });
        const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { defval: '' });
        kitImportRows(rows);
      } catch (e) { console.error(e); showFlash('Fichier Excel/CSV illisible.', true); }
    };
    reader.readAsArrayBuffer(file);
  } else {
    showFlash('Format non reconnu (JSON, Excel ou CSV).', true);
  }
}

// Upsert: match on id, else on (case-insensitive) name.
function kitUpsert(person) {
  const hit = data.find(x => (person.id && x.id === person.id) || x.name.toLowerCase() === person.name.toLowerCase());
  if (hit) { Object.assign(hit, person, { id: hit.id }); return 'upd'; }
  if (!person.id) person.id = gid();
  if (!person.avatarColor) person.avatarColor = avatarColor(person.id);
  data.push(person);
  return 'add';
}

// JSON from the org chart (📦 Exporter pour le kit, or the older Export JSON).
function kitImportJSON(j) {
  const team = j.team || j.people || (Array.isArray(j) ? j : null);
  if (!team) { showFlash('Ce JSON ne contient pas de personnes.', true); return; }
  (j.departments || []).forEach(d => {
    const key = d.key || d.id;
    if (!key) return;
    // Same key, or same label created earlier by a CSV import → one department,
    // adopting the org chart's key so later imports keep matching.
    const ex = departments.find(x => x.key === key) ||
      departments.find(x => d.label && x.label.toLowerCase() === d.label.toLowerCase());
    if (ex) {
      if (ex.key !== key) { data.forEach(p => { if (p.dept === ex.key) p.dept = key; }); ex.key = key; }
      Object.assign(ex, { label: d.label || ex.label, color: d.color || ex.color });
    } else {
      departments.push({ key, label: d.label || key, color: d.color || KIT_PALETTE[departments.length % KIT_PALETTE.length] });
    }
  });
  const list = [];
  // The app's VP sentinel is named "You" when not personalised — skip that placeholder.
  if (j.vp && j.vp.name && j.vp.name !== 'You') list.push(j.vp);
  list.push(...team);
  let add = 0, upd = 0;
  list.forEach(p => {
    if (!p || !p.name) return;
    const dept = departments.some(d => d.key === p.dept) ? p.dept : kitEnsureDept(p.dept === 'all' ? '' : p.dept);
    const r = kitUpsert({
      id: p.id, name: p.name, role: p.role || '', type: p.type || 'employee',
      dept, programs: kitSplitPrograms(p.programs), avatarColor: p.avatarColor || p.avatar_color,
    });
    r === 'add' ? add++ : upd++;
  });
  if (j.cardConfig && typeof _cardCfg !== 'undefined') { Object.assign(_cardCfg, j.cardConfig); _cardSaveCfg(); }
  kitPruneDepts(); kitSave(); render();
  showFlash(`Import : ${add} ajoutée(s), ${upd} mise(s) à jour.`);
}

// Rows from Excel/CSV. Accepts French or English headers, any case/accents.
function kitImportRows(rows) {
  const pick = (r, keys) => {
    for (const k of Object.keys(r)) if (keys.includes(kitSlug(k))) return (r[k] ?? '').toString().trim();
    return '';
  };
  let add = 0, upd = 0, skip = 0;
  rows.forEach(r => {
    const name = pick(r, ['nom', 'name', 'nom_complet', 'full_name']);
    if (!name) { skip++; return; }
    const res = kitUpsert({
      id: pick(r, ['id', 'identifiant', 'no', 'numero']) || undefined,
      name,
      role: pick(r, ['role', 'titre', 'title', 'poste', 'fonction']),
      type: kitNormType(pick(r, ['type', 'statut', 'status'])),
      dept: kitEnsureDept(pick(r, ['departement', 'department', 'dept', 'equipe', 'service'])),
      programs: kitSplitPrograms(pick(r, ['programmes', 'programs', 'programme', 'formations'])),
    });
    res === 'add' ? add++ : upd++;
  });
  kitPruneDepts(); kitSave(); render();
  showFlash(`Import : ${add} ajoutée(s), ${upd} mise(s) à jour${skip ? `, ${skip} ligne(s) sans nom ignorée(s)` : ''}.`, add + upd === 0);
}

function kitRowsForExport() {
  return data.map(p => ({
    id: p.id, nom: p.name, role: p.role || '',
    type: { employee: 'employé', contractor: 'contractuel', lead: 'lead', exec: 'vp' }[p.type] || p.type,
    departement: DM[p.dept] ? DM[p.dept].l : '',
    programmes: (p.programs || []).join('; '),
  }));
}
function kitExportCSV() {
  if (!data.length) { showFlash('Aucune personne à exporter.', true); return; }
  const ws = XLSX.utils.json_to_sheet(kitRowsForExport());
  const csv = '﻿' + XLSX.utils.sheet_to_csv(ws);   // BOM so Excel reads accents correctly
  kitDownload(new Blob([csv], { type: 'text/csv;charset=utf-8' }), `xguard-cartes-personnes-${_cardToday()}.csv`);
}
function kitDownloadTemplate() {
  const rows = [
    { id: '', nom: 'Marie Tremblay', role: 'Formatrice BSP', type: 'employé', departement: 'Formation', programmes: 'BSP; RCR' },
    { id: '', nom: 'Jean Gagnon', role: 'Agent SAC', type: 'contractuel', departement: 'Service Client', programmes: 'SAC' },
  ];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), 'Personnes');
  XLSX.writeFile(wb, 'modele-personnes-cartes.xlsx');
}
function kitDownload(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

// ==================== INIT ====================
function kitInit() {
  kitLoad();
  if (!data.length) _kitView = 'people';
  else { _kitView = 'cards'; document.querySelectorAll('.vtab').forEach(b => b.classList.toggle('active', b.dataset.view === 'cards')); }
  render();
}
