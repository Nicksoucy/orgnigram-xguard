// ==================== VIEW: CARTES (ID CARD PRINTING) ====================
// Generates print-ready ID badges for the people in the org chart, sized to
// the ISO CR-80 card standard (85.6 × 54 mm) used by every HiTi CS-series card
// printer. Two output paths, both landing at exact physical size:
//   • cardsPrint()     → browser print, one card per page  (Ctrl+P → HiTi)
//   • cardsExportPDF() → jsPDF, one card per page          (archive / print later)
// See docs/HITI_PRINTING.md for the HiTi driver setup that makes these print
// edge-to-edge on blank PVC cards.

// Raster scale for the PDF export. CSS is 96 px/in; HiTi CS printers are 300 dpi.
// 300/96 ≈ 3.125, so 3.2 guarantees ≥300 dpi at the card's real size without
// bloating the file the way scale 4 (≈384 dpi) does.
const CARD_PRINT_SCALE = 3.2;

// ---- Card standards (physical, in mm) ----
const CARD_STANDARDS = {
  cr80: { w: 85.6, h: 54,   label: 'CR-80 — 85.6 × 54 mm (standard ID card)' },
  cr79: { w: 83.9, h: 51,   label: 'CR-79 — 83.9 × 51 mm (adhesive)' },
  custom: { w: 85.6, h: 54, label: 'Custom (set size below)' },
};

// ---- Persisted config ----
const CARD_CFG_KEY = 'xgCardCfg';
function _cardDefaults() {
  return {
    standard: 'cr80', wmm: 85.6, hmm: 54,
    orient: 'landscape',          // landscape | portrait
    bleedMm: 0,                   // 0 | 1 | 2  (see HiTi over-the-edge note in docs)
    sides: 'front',               // front | both
    theme: 'light',               // light | dark
    qr: true,
    qrMode: 'link',               // link | vcard
    qrBase: 'https://nicksoucy.github.io/orgnigram-xguard',
    org: 'XGuard', tagline: 'Division Formation',
    accent: '#ff6b35',
    showPrograms: true, showDept: true, showId: true,
    issueDate: '',                // '' → today at render time
  };
}
let _cardCfg = (function () {
  try { return Object.assign(_cardDefaults(), JSON.parse(localStorage.getItem(CARD_CFG_KEY) || '{}')); }
  catch (e) { return _cardDefaults(); }
})();
function _cardSaveCfg() { try { localStorage.setItem(CARD_CFG_KEY, JSON.stringify(_cardCfg)); } catch (e) {} }

// ---- Selection state (Set of person ids) ----
let _cardSel = new Set();
let _cardSettingsOpen = false;

// ---- Physical dimensions incl. bleed ----
function _cardBaseDims() {
  const s = CARD_STANDARDS[_cardCfg.standard] || CARD_STANDARDS.cr80;
  let w = _cardCfg.standard === 'custom' ? (+_cardCfg.wmm || 85.6) : s.w;
  let h = _cardCfg.standard === 'custom' ? (+_cardCfg.hmm || 54) : s.h;
  if (_cardCfg.orient === 'portrait') { const t = w; w = h; h = t; }
  return { w, h };
}
function _cardPageDims() {
  const b = _cardBaseDims(), bl = +_cardCfg.bleedMm || 0;
  return { w: +(b.w + bl * 2).toFixed(2), h: +(b.h + bl * 2).toFixed(2), bleed: bl };
}

function _cardToday() {
  if (_cardCfg.issueDate) return _cardCfg.issueDate;
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ---- QR helper (vendored MIT qrcode-generator → window.qrcode) ----
function _cardQR(text) {
  if (typeof qrcode === 'undefined') return '';
  try {
    const qr = qrcode(0, 'M');       // type 0 = auto-size, error correction M
    qr.addData(text);
    qr.make();
    return qr.createDataURL(6, 2);   // 6px cells, 2-module quiet zone → crisp, scales down cleanly
  } catch (e) { console.warn('QR gen failed:', e); return ''; }
}
function _cardQRPayload(p) {
  if (_cardCfg.qrMode === 'vcard') {
    return `BEGIN:VCARD\nVERSION:3.0\nN:${p.name}\nFN:${p.name}\nORG:${_cardCfg.org};${_cardCfg.tagline}\nTITLE:${p.role || ''}\nEND:VCARD`;
  }
  const base = (_cardCfg.qrBase || '').replace(/\/+$/, '');
  return `${base}/?card=${encodeURIComponent(p.id)}`;
}

// ---- Card HTML (a single physical side) ----
function _cardFrontHTML(p, dims) {
  const cfg = _cardCfg;
  const dept = DM[p.dept];
  const deptColor = (departments.find(d => d.key === p.dept) || {}).color || cfg.accent;
  const progs = (cfg.showPrograms && p.programs && p.programs.length)
    ? p.programs.map(pr => `<span class="pc-prog">${esc(pr)}</span>`).join('') : '';
  const deptChip = (cfg.showDept && dept)
    ? `<span class="pc-dept" style="background:${deptColor};">${esc(dept.l)}</span>` : '';
  const qr = cfg.qr ? `<div class="pc-qr"><img src="${_cardQR(_cardQRPayload(p))}" alt=""></div>` : '';
  const footId = cfg.showId
    ? `<span class="pc-accent"></span><span class="pc-id">${esc(p.id)}</span><span>ÉMIS ${_cardToday()}</span>`
    : `<span class="pc-accent"></span><span>ÉMIS ${_cardToday()}</span>`;
  return `
    <div class="pc-topbar">
      <span class="pc-org">${esc(cfg.org)}</span>
      <span class="pc-tag">${esc(cfg.tagline)}</span>
    </div>
    <div class="pc-body">
      <div class="pc-avatar" style="background:${p.avatarColor || avatarColor(p.id)};">${esc(initials(p.name))}</div>
      <div class="pc-info">
        <div class="pc-name">${esc(p.name)}</div>
        <div class="pc-role">${esc(p.role || bl(p.type))}</div>
        <div class="pc-chips">${deptChip}${progs}</div>
      </div>
      ${qr}
    </div>
    <div class="pc-footer">${footId}<span class="pc-type">${esc(bl(p.type).toUpperCase())}</span></div>`;
}

function _cardBackHTML(p) {
  const cfg = _cardCfg;
  return `
    <div class="pc-back-head">
      <span class="pc-org">${esc(cfg.org)}</span>
      <span class="pc-sub">Carte d'identité</span>
    </div>
    <div class="pc-back-body">
      <div class="pc-back-qr"><img src="${_cardQR(_cardQRPayload(p))}" alt=""></div>
      <div class="pc-back-text">
        <strong>${esc(cfg.org)} — ${esc(cfg.tagline)}</strong>
        Cette carte certifie que le porteur est membre de l'équipe ${esc(cfg.org)}.
        Scannez le code pour vérifier le profil. Si trouvée, retourner à ${esc(cfg.org)}.
      </div>
    </div>
    <div class="pc-back-foot"><span>SIGNATURE</span><span class="pc-sig"></span></div>`;
}

// Build a full .print-card element (returns HTML string). `face` = 'front' | 'back'.
function _cardSideHTML(p, face, dims) {
  const cfg = _cardCfg;
  const cls = ['print-card', face, cfg.orient === 'portrait' ? 'portrait' : '', cfg.theme === 'dark' ? 'theme-dark' : ''].filter(Boolean).join(' ');
  const style = `width:${dims.w}mm;height:${dims.h}mm;--accent:${cfg.accent};--bleed:${dims.bleed}mm;`;
  const inner = face === 'back' ? _cardBackHTML(p) : _cardFrontHTML(p, dims);
  const trim = dims.bleed > 0 ? `<div class="pc-trim"></div>` : '';
  return `<div class="${cls}" style="${style}" data-pid="${esc(p.id)}" data-face="${face}">${inner}${trim}</div>`;
}

// ---- People source (VP + everyone, grouped by department) ----
function _cardPeople() { return allPeople(); }

// ==================== RENDER ====================
function renderCards(ct, cl) {
  const sel = _cardSel;
  cl.innerHTML = `
    <button class="btn primary" onclick="cardsPrint()">🖨 Imprimer (${sel.size})</button>
    <button class="btn" onclick="cardsExportPDF()">📄 Export PDF</button>
    <button class="btn" onclick="cardsSelectAll()">Tout sélectionner</button>
    <button class="btn" onclick="cardsClearSel()">Effacer</button>
    <span style="flex:1"></span>
    <button class="btn" onclick="cardsToggleSettings()">⚙️ Options carte</button>`;

  ct.innerHTML = `
    <div class="cards-settings ${_cardSettingsOpen ? '' : 'hidden'}" id="cardSettings">${_cardSettingsHTML()}</div>
    <div class="cards-wrap">
      <div class="cards-picker">${_cardPickerHTML()}</div>
      <div class="cards-preview">${_cardPreviewHTML()}</div>
    </div>`;
}

function _cardSettingsHTML() {
  const c = _cardCfg;
  const opt = (v, cur, label) => `<option value="${v}"${v === cur ? ' selected' : ''}>${label}</option>`;
  return `
    <div class="cs-field"><label>Format</label>
      <select onchange="cardsSet('standard',this.value)">
        ${Object.entries(CARD_STANDARDS).map(([k, s]) => opt(k, c.standard, s.label)).join('')}
      </select></div>
    ${c.standard === 'custom' ? `
      <div class="cs-field"><label>Largeur (mm)</label><input type="number" step="0.1" value="${c.wmm}" onchange="cardsSet('wmm',parseFloat(this.value))"></div>
      <div class="cs-field"><label>Hauteur (mm)</label><input type="number" step="0.1" value="${c.hmm}" onchange="cardsSet('hmm',parseFloat(this.value))"></div>` : ''}
    <div class="cs-field"><label>Orientation</label>
      <select onchange="cardsSet('orient',this.value)">${opt('landscape', c.orient, 'Paysage')}${opt('portrait', c.orient, 'Portrait')}</select></div>
    <div class="cs-field"><label>Faces</label>
      <select onchange="cardsSet('sides',this.value)">${opt('front', c.sides, 'Recto seul')}${opt('both', c.sides, 'Recto + verso')}</select></div>
    <div class="cs-field"><label>Fond perdu / bleed</label>
      <select onchange="cardsSet('bleedMm',parseFloat(this.value))">${opt(0, c.bleedMm, '0 mm (taille exacte)')}${opt(1, c.bleedMm, '1 mm (recommandé HiTi)')}${opt(2, c.bleedMm, '2 mm')}</select></div>
    <div class="cs-field"><label>Thème</label>
      <select onchange="cardsSet('theme',this.value)">${opt('light', c.theme, 'Clair (économe en ruban)')}${opt('dark', c.theme, 'Foncé')}</select></div>
    <div class="cs-field"><label>Organisation</label><input value="${esc(c.org)}" onchange="cardsSet('org',this.value)"></div>
    <div class="cs-field"><label>Sous-titre</label><input value="${esc(c.tagline)}" onchange="cardsSet('tagline',this.value)"></div>
    <div class="cs-field"><label>Couleur accent</label><input type="color" value="${c.accent}" onchange="cardsSet('accent',this.value)"></div>
    <div class="cs-field"><label>Date d'émission</label><input type="date" value="${c.issueDate}" onchange="cardsSet('issueDate',this.value)"></div>
    <div class="cs-field"><label>QR</label>
      <select onchange="cardsSet('qrMode',this.value)">${opt('link', c.qrMode, 'Lien profil')}${opt('vcard', c.qrMode, 'Contact (vCard)')}</select></div>
    <div class="cs-field"><label>URL de base (QR lien)</label><input value="${esc(c.qrBase)}" onchange="cardsSet('qrBase',this.value)"></div>
    <div class="cs-field inline"><input type="checkbox" id="cs_qr" ${c.qr ? 'checked' : ''} onchange="cardsSet('qr',this.checked)"><label for="cs_qr">Afficher le QR</label></div>
    <div class="cs-field inline"><input type="checkbox" id="cs_dept" ${c.showDept ? 'checked' : ''} onchange="cardsSet('showDept',this.checked)"><label for="cs_dept">Département</label></div>
    <div class="cs-field inline"><input type="checkbox" id="cs_prog" ${c.showPrograms ? 'checked' : ''} onchange="cardsSet('showPrograms',this.checked)"><label for="cs_prog">Programmes</label></div>
    <div class="cs-field inline"><input type="checkbox" id="cs_id" ${c.showId ? 'checked' : ''} onchange="cardsSet('showId',this.checked)"><label for="cs_id">Numéro ID</label></div>`;
}

function _cardPickerHTML() {
  const people = _cardPeople();
  let h = `<h4>Sélection (${_cardSel.size}/${people.length})</h4>`;
  // VP first
  h += _cardPickerRows([VP]);
  departments.forEach(dept => {
    const members = data.filter(p => p.dept === dept.key);
    if (!members.length) return;
    const allSel = members.every(p => _cardSel.has(p.id));
    h += `<div class="cp-dept-h">
      <span class="dept-dot" style="background:${dept.color};"></span>
      <span>${esc(dept.label)}</span>
      <span class="cp-all" onclick="cardsToggleDept('${dept.key}',${!allSel})">${allSel ? 'aucun' : 'tous'}</span>
    </div>`;
    h += _cardPickerRows(members);
  });
  // Any people without a matching department bucket
  const orphans = data.filter(p => !departments.some(d => d.key === p.dept));
  if (orphans.length) { h += `<h4>Autres</h4>` + _cardPickerRows(orphans); }
  return h;
}
function _cardPickerRows(list) {
  return list.map(p => `
    <label class="cp-row">
      <input type="checkbox" ${_cardSel.has(p.id) ? 'checked' : ''} onchange="cardsToggle('${p.id}',this.checked)">
      <span class="cp-name">${esc(p.name)}</span>
      <span class="cp-role">${esc(p.role || bl(p.type))}</span>
    </label>`).join('');
}

function _cardPreviewHTML() {
  const ids = [..._cardSel];
  if (!ids.length) {
    return `<div class="cards-empty">Sélectionnez des personnes à gauche pour prévisualiser les cartes.<br>
      <span style="font-size:11px;">Format actuel : ${_cardPageDims().w} × ${_cardPageDims().h} mm${_cardCfg.sides === 'both' ? ' · recto + verso' : ''}</span></div>`;
  }
  const dims = _cardPageDims();
  const people = _cardPeople();
  let h = `<div class="cards-sheet">`;
  ids.forEach(id => {
    const p = people.find(x => x.id === id);
    if (!p) return;
    h += `<div class="card-pair">
      <span class="cp-label">${esc(p.name)}${_cardCfg.sides === 'both' ? ' · recto' : ''}</span>
      ${_cardSideHTML(p, 'front', dims)}
      ${_cardCfg.sides === 'both' ? `<span class="cp-label">verso</span>${_cardSideHTML(p, 'back', dims)}` : ''}
    </div>`;
  });
  h += `</div>`;
  return h;
}

// ==================== ACTIONS ====================
function cardsSet(key, val) {
  _cardCfg[key] = val;
  if (key === 'standard' && val !== 'custom') {
    _cardCfg.wmm = CARD_STANDARDS[val].w; _cardCfg.hmm = CARD_STANDARDS[val].h;
  }
  _cardSaveCfg();
  render();
}
function cardsToggleSettings() { _cardSettingsOpen = !_cardSettingsOpen; render(); }

function cardsToggle(id, on) { if (on) _cardSel.add(id); else _cardSel.delete(id); render(); }
function cardsToggleDept(key, on) {
  data.filter(p => p.dept === key).forEach(p => { if (on) _cardSel.add(p.id); else _cardSel.delete(p.id); });
  render();
}
function cardsSelectAll() { _cardPeople().forEach(p => _cardSel.add(p.id)); render(); }
function cardsClearSel() { _cardSel.clear(); render(); }

// Inject / update the @page rule so the printer receives the exact card size.
function _cardApplyPageStyle() {
  const d = _cardPageDims();
  let el = document.getElementById('card-page-style');
  if (!el) { el = document.createElement('style'); el.id = 'card-page-style'; document.head.appendChild(el); }
  el.textContent = `@page{size:${d.w}mm ${d.h}mm;margin:0;}`;
}

// Ordered list of {person, face} sides for the current selection.
function _cardSideList() {
  const people = _cardPeople();
  const out = [];
  [..._cardSel].forEach(id => {
    const p = people.find(x => x.id === id);
    if (!p) return;
    out.push({ p, face: 'front' });
    if (_cardCfg.sides === 'both') out.push({ p, face: 'back' });
  });
  return out;
}

// ---- Browser print: one physical card per page ----
function cardsPrint() {
  const sides = _cardSideList();
  if (!sides.length) { showFlash('Aucune carte sélectionnée.', true); return; }
  const dims = _cardPageDims();
  let area = document.getElementById('card-print-area');
  if (!area) { area = document.createElement('div'); area.id = 'card-print-area'; document.body.appendChild(area); }
  area.innerHTML = sides.map(s => _cardSideHTML(s.p, s.face, dims)).join('');
  _cardApplyPageStyle();
  setTimeout(() => window.print(), 60);  // let QR images paint first
}

// ---- PDF export: rasterize each side to its own exact-size page ----
async function cardsExportPDF() {
  const sides = _cardSideList();
  if (!sides.length) { showFlash('Aucune carte sélectionnée.', true); return; }
  if (!window.jspdf || !window.html2canvas) { showFlash('Librairies PDF indisponibles.', true); return; }
  const { jsPDF } = window.jspdf;
  const dims = _cardPageDims();
  const orientation = dims.w >= dims.h ? 'l' : 'p';

  // Off-screen staging so html2canvas captures real-size, un-scaled cards.
  const stage = document.createElement('div');
  stage.style.cssText = 'position:fixed;left:-10000px;top:0;background:#fff;';
  stage.innerHTML = sides.map(s => _cardSideHTML(s.p, s.face, dims)).join('');
  document.body.appendChild(stage);
  // Strip on-screen chrome so the raster is the bare card face (no shadow halo,
  // no rounded transparent corners) — the physical card is already die-cut.
  stage.querySelectorAll('.print-card').forEach(c => { c.style.boxShadow = 'none'; c.style.borderRadius = '0'; });

  showFlash('Génération du PDF…');
  try {
    const pdf = new jsPDF({ unit: 'mm', format: [dims.w, dims.h], orientation });
    const cards = stage.querySelectorAll('.print-card');
    for (let i = 0; i < cards.length; i++) {
      const canvas = await html2canvas(cards[i], { scale: CARD_PRINT_SCALE, backgroundColor: null, logging: false });
      if (i > 0) pdf.addPage([dims.w, dims.h], orientation);
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, dims.w, dims.h);
    }
    pdf.save(`xguard-cartes-${_cardToday()}.pdf`);
    showFlash(`${cards.length} carte(s) exportée(s).`);
  } catch (e) {
    console.error('PDF export failed:', e);
    showFlash('Échec de l\'export PDF.', true);
  } finally {
    document.body.removeChild(stage);
  }
}
