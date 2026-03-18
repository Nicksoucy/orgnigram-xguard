// ==================== VIEW: HORAIRES ====================

// ---- Constants ----

const HOR_PROGRAMS = ['BSP','RCR','Élite','Drone','Secourisme','Anglais'];
const HOR_CATEGORIES = [
  {value:'formation_qc',  label:'Formation QC'},
  {value:'rcr_mtl',       label:'RCR MTL'},
  {value:'classe_mtl',    label:'Classe MTL'},
  {value:'formation_ligne',label:'En ligne'}
];
const HOR_QUARTS = ['Jour','Soir','Weekend'];
const HOR_PROGRAM_COLORS = {
  'BSP':        '#1a73e8',
  'RCR':        '#0d904f',
  'Élite':      '#7b1fa2',
  'Drone':      '#e65100',
  'Secourisme': '#00838f',
  'Anglais':    '#c2185b'
};
const HOR_DAYS_FR = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
const HOR_MONTHS_FR = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];

// ---- State for the open shift modal ----
let _horModalEntry = null;   // null = new, object = editing existing
let _horModalPrefill = {};   // pre-filled values when clicking empty cell

// ---- Day.js helpers ----

function horDayjs() {
  // Ensure dayjs plugins are loaded
  if (window.dayjs && window.dayjs_plugin_isoWeek && !window.dayjs._horPluginsLoaded) {
    try {
      dayjs.extend(window.dayjs_plugin_isoWeek);
      window.dayjs._horPluginsLoaded = true;
    } catch(e) {}
  }
  return window.dayjs;
}

function horCurrentMonday() {
  const dj = horDayjs();
  if (!dj) {
    // Fallback without dayjs
    const today = new Date();
    const dow = today.getDay(); // 0=Sun
    const diff = (dow === 0) ? -6 : 1 - dow;
    const mon = new Date(today);
    mon.setDate(today.getDate() + diff);
    return mon.toISOString().slice(0, 10);
  }
  const today = dj();
  const dow = today.day(); // 0=Sun
  const diff = (dow === 0) ? -6 : 1 - dow;
  return today.add(diff, 'day').format('YYYY-MM-DD');
}

function horWeekDates(mondayStr) {
  const dates = [];
  const dj = horDayjs();
  for (let i = 0; i < 7; i++) {
    if (dj) {
      dates.push(dj(mondayStr).add(i, 'day').format('YYYY-MM-DD'));
    } else {
      const d = new Date(mondayStr);
      d.setDate(d.getDate() + i);
      dates.push(d.toISOString().slice(0, 10));
    }
  }
  return dates;
}

function horWeekEnd(mondayStr) {
  return horWeekDates(mondayStr)[6];
}

function horAddWeeks(mondayStr, n) {
  const dj = horDayjs();
  if (dj) return dj(mondayStr).add(n * 7, 'day').format('YYYY-MM-DD');
  const d = new Date(mondayStr);
  d.setDate(d.getDate() + n * 7);
  return d.toISOString().slice(0, 10);
}

function horFormatDate(dateStr) {
  // Returns "lun. 16 mars"
  const d = new Date(dateStr + 'T00:00:00');
  const dow = HOR_DAYS_FR[d.getDay() === 0 ? 6 : d.getDay() - 1];
  const month = HOR_MONTHS_FR[d.getMonth()];
  return `${dow}. ${d.getDate()} ${month}`;
}

function horWeekLabel(mondayStr) {
  const dates = horWeekDates(mondayStr);
  const start = new Date(mondayStr + 'T00:00:00');
  const end   = new Date(dates[6] + 'T00:00:00');
  const sm = HOR_MONTHS_FR[start.getMonth()];
  const em = HOR_MONTHS_FR[end.getMonth()];
  const sy = start.getFullYear();
  const ey = end.getFullYear();
  if (sy !== ey) return `${start.getDate()} ${sm} ${sy} – ${end.getDate()} ${em} ${ey}`;
  if (sm !== em) return `${start.getDate()} ${sm} – ${end.getDate()} ${em} ${sy}`;
  return `${start.getDate()} – ${end.getDate()} ${sm} ${sy}`;
}

// ---- Color helpers ----

function horProgramColor(program) {
  return HOR_PROGRAM_COLORS[program] || '#60a5fa';
}

function horColorLight(hex) {
  // Returns a lightened/alpha version for backgrounds
  return hex + '22';
}

// ---- Trainer filtering (delegates to shared getTrainers in utils.js) ----

function horGetTrainers() {
  // Note: getTrainers() also includes dept==='sac' — unified criteria
  return getTrainers();
}

// ---- Category label ----

function horCatLabel(cat) {
  const found = HOR_CATEGORIES.find(c => c.value === cat);
  return found ? found.label : cat || '';
}

// ---- Week grid renderer ----

function horBuildGrid(weekDates, trainers, entries, filter) {
  const filtered = filter === 'all'
    ? entries
    : entries.filter(e => e.category === filter);

  // Map entries by instructor_id + date
  const entryMap = {}; // key: `${instructor_id}__${date}` => array of entries
  filtered.forEach(e => {
    const key = `${e.instructor_id}__${e.date}`;
    if (!entryMap[key]) entryMap[key] = [];
    entryMap[key].push(e);
  });

  if (!trainers.length) {
    return `<div class="hor-empty-state">Aucun formateur trouvé dans les données. Ajoutez des membres avec des programmes assignés.</div>`;
  }

  // Build header row
  const headerCells = weekDates.map((d, i) => {
    const dayD = new Date(d + 'T00:00:00');
    const isToday = d === new Date().toISOString().slice(0, 10);
    return `<th class="hor-th${isToday ? ' hor-today' : ''}">
      <div class="hor-th-day">${HOR_DAYS_FR[i]}</div>
      <div class="hor-th-date">${dayD.getDate()} ${HOR_MONTHS_FR[dayD.getMonth()].slice(0,3)}.</div>
    </th>`;
  }).join('');

  // Build rows
  const rows = trainers.map(trainer => {
    const cells = weekDates.map(date => {
      const key = `${trainer.id}__${date}`;
      const cellEntries = entryMap[key] || [];
      const pills = cellEntries.map(e => {
        const color = horProgramColor(e.program);
        const label = (e.cohorts?.code || e.excel_cell_code || '') + (e.program ? ' ' + e.program : '');
        return `<div class="hor-pill" style="background:${color};border-color:${color};"
          onclick="horOpenEntry('${e.id}'); event.stopPropagation();"
          title="${esc(label)} — ${esc(e.start_time||'')}–${esc(e.end_time||'')}${e.notes ? '\n' + e.notes : ''}">
          ${esc(label)}
        </div>`;
      }).join('');
      return `<td class="hor-td" onclick="horClickCell('${trainer.id}','${date}')">
        ${pills}
        <div class="hor-td-add" title="Ajouter un shift">+</div>
      </td>`;
    }).join('');

    const col = avatarColor(trainer.id);
    const ini = initials(trainer.name);
    return `<tr class="hor-row">
      <td class="hor-trainer-cell">
        <div class="hor-trainer-avatar" style="background:${col};">${ini}</div>
        <div class="hor-trainer-info">
          <div class="hor-trainer-name">${esc(trainer.name)}</div>
          <div class="hor-trainer-role">${esc(trainer.role || '')}</div>
        </div>
      </td>
      ${cells}
    </tr>`;
  }).join('');

  return `
    <div class="hor-grid-wrap">
      <table class="hor-grid">
        <thead>
          <tr>
            <th class="hor-th hor-trainer-th">Formateur</th>
            ${headerCells}
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>
  `;
}

// ---- Month view renderer ----

function horBuildMonthView(mondayStr, trainers, entries, filter) {
  const dj = horDayjs();
  const startDate = new Date(mondayStr + 'T00:00:00');
  const year = startDate.getFullYear();
  const month = startDate.getMonth();
  const monthLabel = HOR_MONTHS_FR[month] + ' ' + year;

  // First day of month
  const firstDay = new Date(year, month, 1);
  const lastDay  = new Date(year, month + 1, 0);

  const filtered = filter === 'all' ? entries : entries.filter(e => e.category === filter);

  // Days in month
  const days = [];
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(new Date(year, month, d));
  }

  // Offset: day of week of first day (Mon=0)
  let offset = firstDay.getDay() - 1;
  if (offset < 0) offset = 6; // Sunday → 6

  // Map entries by date
  const entryByDate = {};
  filtered.forEach(e => {
    if (!entryByDate[e.date]) entryByDate[e.date] = [];
    entryByDate[e.date].push(e);
  });

  // Header
  const headerCells = HOR_DAYS_FR.map(d => `<th class="hor-mcal-th">${d}</th>`).join('');

  // Calendar cells
  let cells = '';
  const todayStr = new Date().toISOString().slice(0, 10);
  let dayIdx = 0;

  // Empty cells before first day
  for (let i = 0; i < offset; i++) {
    cells += '<td class="hor-mcal-td hor-mcal-empty"></td>';
    dayIdx++;
  }

  days.forEach(d => {
    const dateStr = d.toISOString().slice(0, 10);
    const isToday = dateStr === todayStr;
    const dayEntries = entryByDate[dateStr] || [];

    const pills = dayEntries.slice(0, 3).map(e => {
      const color = horProgramColor(e.program);
      const label = (e.cohorts?.code || e.excel_cell_code || '') + ' ' + (e.program || '');
      return `<div class="hor-mcal-pill" style="background:${color};" title="${esc(label)}"
        onclick="horOpenEntry('${e.id}'); event.stopPropagation();">${esc(label.trim())}</div>`;
    }).join('');

    const overflow = dayEntries.length > 3
      ? `<div class="hor-mcal-more">+${dayEntries.length - 3} autres</div>`
      : '';

    cells += `<td class="hor-mcal-td${isToday ? ' hor-today' : ''}" onclick="horClickCell('','${dateStr}')">
      <div class="hor-mcal-day-num${isToday ? ' hor-today-num' : ''}">${d.getDate()}</div>
      ${pills}${overflow}
    </td>`;
    dayIdx++;

    if (dayIdx % 7 === 0 && d.getDate() < lastDay.getDate()) cells += '</tr><tr>';
  });

  // Fill trailing empty cells
  const remaining = 7 - (dayIdx % 7 === 0 ? 0 : dayIdx % 7);
  if (remaining < 7) {
    for (let i = 0; i < remaining; i++) cells += '<td class="hor-mcal-td hor-mcal-empty"></td>';
  }

  return `
    <div class="hor-month-label">${HOR_MONTHS_FR[month].charAt(0).toUpperCase() + HOR_MONTHS_FR[month].slice(1)} ${year}</div>
    <div class="hor-grid-wrap">
      <table class="hor-mcal">
        <thead><tr>${headerCells}</tr></thead>
        <tbody><tr>${cells}</tr></tbody>
      </table>
    </div>
  `;
}

// ---- Legend HTML ----

function horLegendHTML() {
  return `<div class="hor-legend">` +
    Object.entries(HOR_PROGRAM_COLORS).map(([prog, color]) =>
      `<span class="hor-legend-chip" style="background:${color}22;border:1px solid ${color};color:${color};">${prog}</span>`
    ).join('') +
    `</div>`;
}

// ---- Modal HTML ----

function horModalHTML() {
  const trainers = horGetTrainers();
  const trainerOptions = trainers.map(t =>
    `<option value="${t.id}">${esc(t.name)}</option>`
  ).join('');

  const programOptions = HOR_PROGRAMS.map(p =>
    `<option value="${p}">${p}</option>`
  ).join('');

  const catOptions = HOR_CATEGORIES.map(c =>
    `<option value="${c.value}">${c.label}</option>`
  ).join('');

  const quartOptions = HOR_QUARTS.map(q =>
    `<option value="${q.toLowerCase()}">${q}</option>`
  ).join('');

  const locationOptions = _horLocations.length
    ? _horLocations.map(l => `<option value="${l.id}">${esc(l.name)}</option>`).join('')
    : '<option value="">— Aucune salle —</option>';

  const isEdit = !!_horModalEntry;
  const pf = _horModalPrefill;
  const e  = _horModalEntry || {};

  return `
  <div class="hor-modal-overlay" id="hor-modal-overlay" onclick="horCloseModal(event)">
    <div class="hor-modal" onclick="event.stopPropagation()">
      <div class="hor-modal-header">
        <h3 class="hor-modal-title">${isEdit ? 'Modifier le shift' : 'Nouveau shift'}</h3>
        <button class="hor-modal-close" onclick="horCloseModal()">✕</button>
      </div>

      <div class="hor-modal-body">
        <div class="hor-modal-row hor-modal-row-2">
          <div class="hor-field">
            <label class="hor-label">Instructeur</label>
            <select class="hor-input" id="hm_instructor">
              ${trainerOptions}
            </select>
          </div>
          <div class="hor-field">
            <label class="hor-label">Programme</label>
            <select class="hor-input" id="hm_program">
              ${programOptions}
            </select>
          </div>
        </div>

        <div class="hor-modal-row hor-modal-row-2">
          <div class="hor-field">
            <label class="hor-label">Catégorie</label>
            <select class="hor-input" id="hm_category">
              <option value="">— Sélectionner —</option>
              ${catOptions}
            </select>
          </div>
          <div class="hor-field">
            <label class="hor-label">Code cohorte</label>
            <input class="hor-input" type="text" id="hm_cohort" placeholder="ex: JL52" value="${esc(e.excel_cell_code || '')}"/>
          </div>
        </div>

        <div class="hor-modal-row hor-modal-row-2">
          <div class="hor-field">
            <label class="hor-label">Salle</label>
            <select class="hor-input" id="hm_location">
              <option value="">— Aucune salle —</option>
              ${locationOptions}
            </select>
          </div>
          <div class="hor-field">
            <label class="hor-label">Quart</label>
            <select class="hor-input" id="hm_quart">
              ${quartOptions}
            </select>
          </div>
        </div>

        <div class="hor-modal-row">
          <div class="hor-field">
            <label class="hor-label">Date</label>
            <input class="hor-input" type="date" id="hm_date" value="${e.date || pf.date || ''}"/>
          </div>
        </div>

        <div class="hor-modal-row hor-modal-row-2">
          <div class="hor-field">
            <label class="hor-label">Heure début</label>
            <input class="hor-input" type="time" id="hm_start" value="${e.start_time || '09:00'}"/>
          </div>
          <div class="hor-field">
            <label class="hor-label">Heure fin</label>
            <input class="hor-input" type="time" id="hm_end" value="${e.end_time || '17:00'}"/>
          </div>
        </div>

        <div class="hor-modal-row">
          <div class="hor-field">
            <label class="hor-label">Notes</label>
            <textarea class="hor-input hor-textarea" id="hm_notes" placeholder="Notes facultatives...">${esc(e.notes || '')}</textarea>
          </div>
        </div>
      </div>

      <div class="hor-modal-footer">
        ${isEdit ? `<button class="btn danger" onclick="horDeleteEntry('${e.id}')">Supprimer</button>` : '<span></span>'}
        <div style="display:flex;gap:8px;">
          <button class="btn" onclick="horCloseModal()">Annuler</button>
          <button class="btn primary" onclick="horSaveEntry()">Enregistrer</button>
        </div>
      </div>
    </div>
  </div>`;
}

// Pre-fill selects after modal is in DOM
function horModalPrefillSelects() {
  const e  = _horModalEntry || {};
  const pf = _horModalPrefill;

  const sel = (id, val) => {
    const el = document.getElementById(id);
    if (el && val) el.value = val;
  };

  sel('hm_instructor', e.instructor_id || pf.instructor_id || '');
  sel('hm_program',    e.program       || pf.program       || 'BSP');
  sel('hm_category',   e.category      || pf.category      || '');
  sel('hm_quart',      e.quart         || 'jour');
  sel('hm_location',   e.location_id   || '');
}

// ---- Modal actions ----

function horOpenNewShift(prefill) {
  _horModalEntry  = null;
  _horModalPrefill = prefill || {};
  _renderHorModal();
}

function horOpenEntry(entryId) {
  const entry = _horEntries.find(e => e.id === entryId);
  if (!entry) return;
  _horModalEntry  = entry;
  _horModalPrefill = {};
  _renderHorModal();
}

function _renderHorModal() {
  // Remove existing modal if any
  const existing = document.getElementById('hor-modal-overlay');
  if (existing) existing.remove();

  const div = document.createElement('div');
  div.innerHTML = horModalHTML();
  document.body.appendChild(div.firstElementChild);

  horModalPrefillSelects();
}

function horCloseModal(e) {
  if (e && e.target && e.target.id !== 'hor-modal-overlay') return;
  const overlay = document.getElementById('hor-modal-overlay');
  if (overlay) overlay.remove();
}

function horClickCell(instructorId, date) {
  horOpenNewShift({ instructor_id: instructorId, date: date });
}

async function horSaveEntry() {
  const get = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };

  const instructor_id = get('hm_instructor');
  const program       = get('hm_program');
  const category      = get('hm_category') || null;
  const excel_cell_code = get('hm_cohort') || null;
  const location_id   = get('hm_location') || null;
  const quart         = get('hm_quart') || null;
  const date          = get('hm_date');
  const start_time    = get('hm_start') || '09:00';
  const end_time      = get('hm_end')   || '17:00';
  const notes         = get('hm_notes') || null;

  if (!instructor_id) { alert('Veuillez sélectionner un instructeur.'); return; }
  if (!date)          { alert('Veuillez choisir une date.');            return; }

  const payload = {
    instructor_id, program, category, excel_cell_code,
    location_id, quart, date, start_time, end_time, notes,
    status: 'scheduled'
  };

  const saveBtn = document.querySelector('#hor-modal-overlay .btn.primary');
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Enregistrement...'; }

  try {
    if (_horModalEntry) {
      await dbUpdateScheduleEntry(_horModalEntry.id, payload);
    } else {
      await dbSaveScheduleEntry(payload);
    }
    horCloseModal();
    await horReloadEntries();
    horFlash('Shift enregistré');
  } catch(err) {
    console.error('horSaveEntry error:', err);
    alert('Erreur lors de la sauvegarde: ' + (err.message || err));
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Enregistrer'; }
  }
}

async function horDeleteEntry(entryId) {
  if (!confirm('Supprimer ce shift? Cette action est irréversible.')) return;
  try {
    await dbDeleteScheduleEntry(entryId);
    horCloseModal();
    await horReloadEntries();
    horFlash('Shift supprimé', true);
  } catch(err) {
    console.error('horDeleteEntry error:', err);
    alert('Erreur: ' + (err.message || err));
  }
}

async function horCopyWeek() {
  const targetStart = horAddWeeks(_horCurrentWeek, 1);
  if (!confirm(`Copier les shifts de cette semaine vers la semaine du ${horWeekLabel(targetStart)}?`)) return;
  try {
    const n = await dbCopyWeek(_horCurrentWeek, targetStart);
    horFlash(`${n} shift(s) copié(s) vers la semaine suivante`);
  } catch(err) {
    console.error('horCopyWeek error:', err);
    alert('Erreur: ' + (err.message || err));
  }
}

// ---- Reload entries and re-render grid only ----

async function horReloadEntries() {
  try {
    const weekEnd = horWeekEnd(_horCurrentWeek);
    _horEntries = await dbGetScheduleWeek(_horCurrentWeek, weekEnd);
  } catch(e) {
    console.error('horReloadEntries error:', e);
    _horEntries = [];
  }
  horRenderGrid();
}

function horRenderGrid() {
  const wrap = document.getElementById('hor-grid-area');
  if (!wrap) return;
  const trainers  = horGetTrainers();
  const weekDates = horWeekDates(_horCurrentWeek);

  if (_horViewMode === 'month') {
    wrap.innerHTML = horBuildMonthView(_horCurrentWeek, trainers, _horEntries, _horFilter);
  } else {
    wrap.innerHTML = horBuildGrid(weekDates, trainers, _horEntries, _horFilter);
  }
}

// ---- Navigation ----

function horNavWeek(delta) {
  _horCurrentWeek = horAddWeeks(_horCurrentWeek, delta);
  // Update week label without full re-render
  const lbl = document.getElementById('hor-week-label');
  if (lbl) lbl.textContent = horWeekLabel(_horCurrentWeek);
  horReloadEntries();
}

function horSetFilter(val) {
  _horFilter = val;
  // Update active state on filter buttons
  document.querySelectorAll('.hor-filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === val);
  });
  horRenderGrid();
}

function horSetView(mode) {
  _horViewMode = mode;
  document.querySelectorAll('.hor-view-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === mode);
  });
  horRenderGrid();
}

// ---- Flash notification (delegates to shared showFlash in utils.js) ----

function horFlash(msg, isDanger) { showFlash(msg, isDanger); }

// ---- Main render entry point ----

async function renderHoraires(ct, cl) {
  // Init week if needed
  if (!_horCurrentWeek) {
    _horCurrentWeek = horCurrentMonday();
  }

  // Controls bar
  cl.innerHTML = `
    <div class="hor-controls">
      <div class="hor-week-nav">
        <button class="btn hor-nav-btn" onclick="horNavWeek(-1)" title="Semaine précédente">&#8592;</button>
        <span class="hor-week-label" id="hor-week-label">${horWeekLabel(_horCurrentWeek)}</span>
        <button class="btn hor-nav-btn" onclick="horNavWeek(1)" title="Semaine suivante">&#8594;</button>
      </div>

      <div class="hor-view-toggle">
        <button class="btn hor-view-btn${_horViewMode === 'week' ? ' active' : ''}" data-view="week" onclick="horSetView('week')">Semaine</button>
        <button class="btn hor-view-btn${_horViewMode === 'month' ? ' active' : ''}" data-view="month" onclick="horSetView('month')">Mois</button>
      </div>

      <div class="hor-filters">
        <button class="btn hor-filter-btn${_horFilter === 'all' ? ' active' : ''}" data-filter="all" onclick="horSetFilter('all')">Tous</button>
        ${HOR_CATEGORIES.map(c =>
          `<button class="btn hor-filter-btn${_horFilter === c.value ? ' active' : ''}" data-filter="${c.value}" onclick="horSetFilter('${c.value}')">${c.label}</button>`
        ).join('')}
      </div>

      <div class="hor-actions">
        <button class="btn primary" onclick="horOpenNewShift({})">+ Nouveau shift</button>
        <button class="btn" onclick="horCopyWeek()">Copier semaine &#8594;</button>
      </div>
    </div>
  `;

  // Main content skeleton
  ct.innerHTML = `
    <div class="hor-main">
      <div class="hor-notice">
        📅 Vue calendrier combinée — pour gérer les shifts, cohortes et séries, utilisez
        <button class="btn" style="font-size:11px;padding:3px 10px;" onclick="switchView('schedule',document.querySelector('.vtab[onclick*=schedule]'))">📆 Planning</button>
      </div>
      ${horLegendHTML()}
      <div id="hor-grid-area" class="hor-grid-area">
        <div class="hor-loading">Chargement des horaires...</div>
      </div>
    </div>
  `;

  // Load data
  try {
    const weekEnd = horWeekEnd(_horCurrentWeek);
    [_horLocations, _horEntries] = await Promise.all([
      dbGetLocations().catch(() => []),
      dbGetScheduleWeek(_horCurrentWeek, weekEnd).catch(() => [])
    ]);
  } catch(e) {
    console.error('renderHoraires load error:', e);
    _horLocations = [];
    _horEntries   = [];
  }

  horRenderGrid();
}
