// ==================== SCHEDULE: MAIN ====================

// ---- Navigation ----

function schedNavMonth(delta) {
  _schedMonth += delta;
  if (_schedMonth > 12) { _schedMonth = 1;  _schedYear++; }
  if (_schedMonth < 1)  { _schedMonth = 12; _schedYear--; }
  _schedWeekStart = null; // reset week on month nav
  schedReloadAndRender();
}

function schedNavWeek(delta) {
  if (!_schedWeekStart) _schedWeekStart = schedGetWeekStart(_schedYear, _schedMonth);
  const d = new Date(_schedWeekStart);
  d.setDate(d.getDate() + delta * 7);
  _schedWeekStart = d;
  schedRenderContent();
}

function schedSetView(v) {
  _schedView = v;
  document.querySelectorAll('.sched-view-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === v);
  });
  schedRenderContent();
}

function schedSetTrainerFilter(v) {
  _schedTrainer = v || null;
  schedRenderContent();
}

function schedSetProgramFilter(v) {
  _schedProgram = v || null;
  schedRenderContent();
}

function schedSelectTrainer(id) {
  _schedTrainer = id;
  schedRenderContent();
}

// ---- Reload ----

async function schedReloadEntries() {
  try {
    _schedEntries = await dbGetScheduleEntries(_schedMonth, _schedYear);
  } catch(e) {
    console.error('schedReloadEntries error:', e);
    _schedEntries = [];
  }
  schedRenderContent();
}

async function schedReloadAndRender() {
  const wrap = document.getElementById('sched-content-area');
  if (wrap) wrap.innerHTML = `<div class="hor-loading">Chargement...</div>`;
  try {
    _schedEntries = await dbGetScheduleEntries(_schedMonth, _schedYear);
  } catch(e) {
    console.error('schedReloadAndRender error:', e);
    _schedEntries = [];
  }
  // Update month label
  const lbl = document.getElementById('sched-month-label');
  if (lbl) lbl.textContent = schedMonthLabel();
  schedRenderContent();
}

function schedRenderContent() {
  const wrap = document.getElementById('sched-content-area');
  if (!wrap) return;
  if (_schedView === 'grid')    wrap.innerHTML = schedBuildMonthGrid();
  else if (_schedView === 'week') wrap.innerHTML = schedBuildWeekView();
  else if (_schedView === 'trainer') wrap.innerHTML = schedBuildTrainerView();
}

// ---- Flash ----

function schedFlash(msg, isDanger) {
  const el = document.createElement('div');
  el.className = 'hor-flash' + (isDanger ? ' danger' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 400); }, 2800);
}

// ---- Week start state ----
let _schedWeekStart = null;

// ---- Main render entry point ----

async function renderSchedule(ct, cl) {
  // Load saved trainer order on first render
  if (!_schedTrainerOrder || !_schedTrainerOrder.length) {
    _schedTrainerOrder = dbLoadTrainerOrder();
  }
  // Initialize week start
  if (!_schedWeekStart) _schedWeekStart = schedGetWeekStart(_schedYear, _schedMonth);

  // Build trainer dropdown options
  const trainerFilterOpts = `<option value="">Tous les formateurs</option>` +
    schedBuildTrainerOpts(_schedTrainer);

  // Build program dropdown options
  const programFilterOpts = `<option value="">Tous les programmes</option>` +
    schedBuildProgramOpts(_schedProgram);

  // Controls bar
  cl.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%;">
      <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
        <button class="btn" style="font-size:14px;padding:5px 10px;" onclick="schedNavMonth(-1)">&#8592;</button>
        <span id="sched-month-label" style="font-size:13px;font-weight:600;min-width:140px;text-align:center;">${esc(schedMonthLabel())}</span>
        <button class="btn" style="font-size:14px;padding:5px 10px;" onclick="schedNavMonth(1)">&#8594;</button>
      </div>

      <div style="display:flex;gap:0;flex-shrink:0;">
        <button class="btn sched-view-btn${_schedView === 'grid' ? ' active' : ''}" data-view="grid"
          style="border-radius:6px 0 0 6px;border-right-width:0;font-size:11px;"
          onclick="schedSetView('grid')">Grille mensuelle</button>
        <button class="btn sched-view-btn${_schedView === 'week' ? ' active' : ''}" data-view="week"
          style="border-radius:0;border-right-width:0;font-size:11px;"
          onclick="schedSetView('week')">Hebdomadaire</button>
        <button class="btn sched-view-btn${_schedView === 'trainer' ? ' active' : ''}" data-view="trainer"
          style="border-radius:0 6px 6px 0;font-size:11px;"
          onclick="schedSetView('trainer')">Par trainer</button>
      </div>

      <select onchange="schedSetTrainerFilter(this.value)"
        style="font-family:'DM Sans',sans-serif;font-size:12px;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--s);color:var(--t);outline:none;cursor:pointer;">
        ${trainerFilterOpts}
      </select>

      <select onchange="schedSetProgramFilter(this.value)"
        style="font-family:'DM Sans',sans-serif;font-size:12px;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--s);color:var(--t);outline:none;cursor:pointer;">
        ${programFilterOpts}
      </select>

      <div style="display:flex;gap:6px;margin-left:auto;">
        <button class="btn" style="font-size:12px;" onclick="schedOpenRecurring('recurring')">🔁 Horaire récurrent</button>
        <button class="btn" style="font-size:12px;" onclick="schedOpenRecurring('pattern')">📋 Pattern cohorte</button>
        <button class="btn" style="font-size:12px;" onclick="schedOpenAutoRules()">⚙️ Règles auto</button>
        <button class="btn primary" style="font-size:12px;" onclick="schedOpenNewShift({})">+ Nouveau shift</button>
      </div>
    </div>`;

  // Main content area
  ct.innerHTML = `
    <div id="sched-content-area">
      <div class="hor-loading">Chargement des horaires...</div>
    </div>`;

  // Escape keydown closes popup/modal
  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape') { schedClosePopup(); schedCloseModal(); }
  });

  // Load data
  try {
    const [entries, locations, progs] = await Promise.all([
      dbGetScheduleEntries(_schedMonth, _schedYear).catch(() => []),
      dbGetLocations().catch(() => []),
      dbGetPrograms().catch(() => [])
    ]);
    _schedEntries   = entries;
    _schedLocations = locations;
    if (progs && progs.length) _schedPrograms = progs;
  } catch(e) {
    console.error('renderSchedule load error:', e);
    _schedEntries   = [];
    _schedLocations = [];
  }

  schedRenderContent();
}
