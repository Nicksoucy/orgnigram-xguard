// ==================== VIEW: SCHEDULE (Module Horaires) ====================

// ---- Constants ----

const SCHED_MONTHS_FR = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
const SCHED_DAYS_FR   = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];

const SCHED_STATUS_LABELS = {
  scheduled:   'Planifié',
  confirmed:   'Confirmé',
  holiday:     'Férié',
  vacation:    'Vacances',
  unavailable: 'Indisponible',
  replacement: 'Remplacement',
  cancelled:   'Annulé'
};

const SCHED_STATUS_COLORS = {
  scheduled:   '#3b82f6',
  confirmed:   '#10b981',
  holiday:     '#374151',
  vacation:    '#1e3a5f',
  unavailable: '#374151',
  replacement: '#78350f',
  cancelled:   '#7f1d1d'
};

// Default program colors fallback (overridden by DB data)
const SCHED_DEFAULT_PROGRAM_COLORS = {
  'BSP':           '#3b82f6',
  'RCR':           '#10b981',
  'ELITE':         '#8b5cf6',
  'DRONE':         '#f97316',
  'SECOURISME':    '#ef4444',
  'CV_PLACEMENT':  '#06b6d4',
  'GESTION_CRISE': '#dc2626',
  'ANGLAIS_BSP':   '#f59e0b',
  'SAC_MATIN':     '#f472b6',
  'SAC_SOIR':      '#ec4899',
  'SAC_WEEKEND':   '#db2777',
  'COORDINATION':  '#64748b',
  'VENTES':        '#fbbf24',
  'RECRUTEMENT':   '#a78bfa',
  'FILMAGE':       '#7c3aed'
};

// ---- State for shift modal ----
let _schedModalEntry  = null;   // null = new, object = editing existing
let _schedModalPrefill = {};    // prefill values when clicking empty cell

// ---- Multi-select state (Ctrl+click) ----
let _schedSelection = {};  // { 'trainerId|dateStr|quart': true }
let _schedSelTrainer = null; // trainer locked during multi-select

// ---- Helpers ----

function schedProgramColor(programId) {
  if (_schedPrograms && _schedPrograms.length) {
    const p = _schedPrograms.find(p => p.id === programId);
    if (p) return p.color;
  }
  return SCHED_DEFAULT_PROGRAM_COLORS[programId] || '#60a5fa';
}

function schedProgramLabel(programId) {
  if (_schedPrograms && _schedPrograms.length) {
    const p = _schedPrograms.find(p => p.id === programId);
    if (p) return p.label;
  }
  return programId || '';
}

function schedMonthLabel() {
  return SCHED_MONTHS_FR[_schedMonth - 1] + ' ' + _schedYear;
}

function schedDaysInMonth(month, year) {
  return new Date(year, month, 0).getDate();
}

function schedTodayStr() {
  return new Date().toISOString().slice(0, 10);
}

function schedDateStr(year, month, day) {
  return year + '-' + String(month).padStart(2, '0') + '-' + String(day).padStart(2, '0');
}

function schedIsWeekend(year, month, day) {
  const d = new Date(year, month - 1, day).getDay(); // 0=Sun, 6=Sat
  return d === 0 || d === 6;
}

function schedDayOfWeek(dateStr) {
  // Returns 0=Mon … 6=Sun
  const d = new Date(dateStr + 'T00:00:00').getDay();
  return d === 0 ? 6 : d - 1;
}

// Get people who are trainers (training dept / have programs / contractor type)
function schedGetTrainers() {
  return data.filter(p =>
    p.type !== 'exec' &&
    (p.dept === 'training' || p.dept === 'sac' || (p.programs && p.programs.length > 0))
  );
}

// ---- Get cell display text from entry ----
function schedCellContent(entry) {
  if (!entry) return '';
  const status = entry.status || 'scheduled';
  if (status === 'holiday')     return 'F';
  if (status === 'vacation')    return 'V';
  if (status === 'cancelled')   return 'CANCEL';
  if (status === 'unavailable') return 'OFF';
  if (status === 'replacement') return 'REMPL';
  // Normal: show cohort code or program short
  const code = (entry.cohorts && entry.cohorts.code) || entry.excel_cell_code || '';
  return code || (entry.program ? entry.program.substring(0, 6) : '?');
}

// Full tooltip text for cell hover
function schedCellTooltip(entry) {
  if (!entry) return '';
  const parts = [];
  const prog = schedProgramLabel(entry.program) || entry.program || '';
  if (prog) parts.push(prog);
  const code = (entry.cohorts && entry.cohorts.code) || entry.excel_cell_code || '';
  if (code) parts.push('Cohorte: ' + code);
  if (entry.start_time && entry.end_time) parts.push(entry.start_time + ' – ' + entry.end_time);
  if (entry.session_id) parts.push('ID: ' + entry.session_id);
  if (entry.quart) parts.push(entry.quart);
  return parts.join(' | ');
}

function schedCellClass(entry) {
  if (!entry) return '';
  const status = entry.status || 'scheduled';
  if (status === 'holiday' || status === 'unavailable') return 'status-holiday';
  if (status === 'vacation')   return 'status-vacation';
  if (status === 'cancelled')  return 'status-cancelled';
  if (status === 'replacement') return 'status-replacement';
  return '';
}

function schedCellBg(entry) {
  if (!entry) return '';
  const status = entry.status || 'scheduled';
  if (['holiday','unavailable','vacation','cancelled','replacement'].includes(status)) return '';
  return schedProgramColor(entry.program);
}

// ---- VIEW 1: Grille Mensuelle ----

function schedBuildMonthGrid() {
  const days    = schedDaysInMonth(_schedMonth, _schedYear);
  const todayS  = schedTodayStr();
  const trainers = schedGetTrainers();

  // Apply trainer filter
  const filteredTrainers = _schedTrainer
    ? trainers.filter(t => t.id === _schedTrainer)
    : trainers;

  // Apply program filter: only show trainers who have entries for that program
  let entries = _schedEntries;
  if (_schedProgram) {
    entries = entries.filter(e => e.program === _schedProgram);
  }

  // Map entries: instructor_id -> date -> [entries]
  const entryMap = {};
  entries.forEach(e => {
    if (!entryMap[e.instructor_id]) entryMap[e.instructor_id] = {};
    const d = e.date;
    if (!entryMap[e.instructor_id][d]) entryMap[e.instructor_id][d] = [];
    entryMap[e.instructor_id][d].push(e);
  });

  // Determine which trainers to show
  let activeTrainers;
  if (_schedProgram) {
    // Program filter: only trainers with matching entries
    activeTrainers = filteredTrainers.filter(t => entryMap[t.id] && Object.keys(entryMap[t.id]).length > 0);
  } else {
    // No program filter: show everyone (so newly added shifts appear)
    activeTrainers = filteredTrainers;
  }

  // Build rows: one default row per trainer + any manually added extra rows
  // Extra rows stored in _schedExtraRows[trainerId] = ['soir','weekend',...]
  if (!window._schedExtraRows) window._schedExtraRows = {};
  const rows = [];
  activeTrainers.forEach(trainer => {
    // Always one default row (no label)
    rows.push({ trainer, quart: null, label: null });
    // Extra rows manually added
    const extras = window._schedExtraRows[trainer.id] || [];
    extras.forEach(q => rows.push({ trainer, quart: q, label: q }));
  });

  // Build day headers — show "Lun\n1" style
  let headerHTML = `<th class="trainer-col">
    Formateur
    <div style="font-size:8px;font-weight:400;color:var(--td);margin-top:2px;">+ ligne</div>
  </th>`;
  for (let d = 1; d <= days; d++) {
    const dateS = schedDateStr(_schedYear, _schedMonth, d);
    const isToday = dateS === todayS;
    const isWe   = schedIsWeekend(_schedYear, _schedMonth, d);
    const dow    = SCHED_DAYS_FR[schedDayOfWeek(dateS)];
    const color  = isToday ? 'var(--a)' : isWe ? 'var(--td)' : 'inherit';
    const opacity = isWe ? 'opacity:0.6;' : '';
    headerHTML += `<th style="color:${color};${opacity}line-height:1.2;">
      <div style="font-size:9px;font-weight:500;">${dow}</div>
      <div style="font-size:11px;font-weight:700;">${d}</div>
    </th>`;
  }

  // Build body rows
  let bodyHTML = '';
  rows.forEach(({ trainer, quart, label }) => {
    const col = avatarColor(trainer.id);
    const ini = initials(trainer.name);
    const tEntries = entryMap[trainer.id] || {};

    const isLastRowForTrainer = !rows.find((r,ri) => ri > rows.indexOf(rows.find(x=>x===({trainer,quart,label}))) && r.trainer.id===trainer.id);
    bodyHTML += `<tr data-trainer="${esc(trainer.id)}" data-quart="${esc(quart||'')}">`;
    bodyHTML += `<td class="trainer-name">
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(trainer.name)}</div>
          ${label ? `<div class="shift-label" style="color:var(--a);font-size:9px;">[${esc(label)}]</div>` : ''}
        </div>
        <button onclick="schedAddRow('${esc(trainer.id)}')" title="Ajouter une ligne" style="background:none;border:none;color:var(--td);cursor:pointer;font-size:14px;padding:0 2px;flex-shrink:0;" onmouseover="this.style.color='var(--a)'" onmouseout="this.style.color='var(--td)'">+</button>
      </div>
    </td>`;

    for (let d = 1; d <= days; d++) {
      const dateS  = schedDateStr(_schedYear, _schedMonth, d);
      const isToday = dateS === todayS;
      const isWe   = schedIsWeekend(_schedYear, _schedMonth, d);
      const dayArr = tEntries[dateS] || [];

      // Filter by quart if needed
      let matchEntries = dayArr;
      if (quart) {
        matchEntries = dayArr.filter(e => (e.quart || '').toLowerCase() === quart);
        if (!matchEntries.length && dayArr.length) matchEntries = [];
      }

      const entry = matchEntries[0] || null;

      const tdClass = [isToday ? 'today' : '', isWe ? 'weekend-col' : ''].filter(Boolean).join(' ');
      const escapedDateS = esc(dateS);
      const escapedId    = entry ? esc(entry.id) : '';
      const trainerId    = esc(trainer.id);

      const selKey = `${trainer.id}|${dateS}|${quart||''}`;
      const isSelected = !!_schedSelection[selKey];
      const selStyle = isSelected ? 'outline:2px solid var(--a);outline-offset:-2px;' : '';

      if (entry) {
        const cellText   = schedCellContent(entry);
        const cellTip    = schedCellTooltip(entry);
        const cellClass  = schedCellClass(entry);
        const cellBg     = schedCellBg(entry);
        const bgStyle    = cellBg ? `background:${cellBg};color:#fff;` : '';
        // Show session_id as tiny bottom line if it exists
        const sessionLine = entry.session_id
          ? `<div style="font-size:7px;opacity:0.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px;font-family:'Space Mono',monospace;">${esc(entry.session_id.split('-').slice(-1)[0])}</div>`
          : '';
        bodyHTML += `<td class="${tdClass}" style="${selStyle}" onclick="schedCellClick('${escapedId}','${trainerId}','${escapedDateS}','${quart||''}',event)">
          <span class="sched-cell ${cellClass}" style="${bgStyle};display:flex;flex-direction:column;align-items:center;" title="${esc(cellTip)}">
            <span>${esc(cellText)}</span>${sessionLine}
          </span>
        </td>`;
      } else {
        bodyHTML += `<td class="${tdClass}" style="${selStyle}" onclick="schedCellClick(null,'${trainerId}','${escapedDateS}','${quart||''}',event)">
          <span class="sched-cell empty-cell">+</span>
        </td>`;
      }
    }

    bodyHTML += `</tr>`;
  });

  if (!rows.length) {
    return `<div class="hor-empty-state">Aucun formateur avec des shifts ce mois-ci. Cliquez sur "+ Nouveau shift" pour en ajouter.</div>`;
  }

  const selCount = Object.keys(_schedSelection).length;
  const selToolbar = selCount > 0 ? `
    <div style="position:sticky;top:0;z-index:10;background:rgba(255,107,53,0.15);border:1px solid var(--a);border-radius:8px;padding:8px 14px;margin-bottom:8px;display:flex;align-items:center;gap:12px;">
      <span style="color:var(--a);font-weight:700;">✓ ${selCount} date${selCount>1?'s':''} sélectionnée${selCount>1?'s':''}</span>
      <span style="color:var(--td);font-size:12px;">${Object.values(_schedSelection).map(s=>s.dateStr).sort().join(', ')}</span>
      <button onclick="schedCreateBulkShifts()" style="margin-left:auto;background:var(--a);color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-weight:700;">Créer ${selCount} shift${selCount>1?'s':''}</button>
      <button onclick="schedClearSelection()" style="background:var(--s);color:var(--td);border:1px solid var(--b);border-radius:6px;padding:6px 10px;cursor:pointer;">✕</button>
    </div>` : '';

  return `${selToolbar}<div id="sched-wrap">
    <table class="sched-grid">
      <thead><tr>${headerHTML}</tr></thead>
      <tbody>${bodyHTML}</tbody>
    </table>
  </div>
  <div style="margin-top:8px;font-size:11px;color:var(--td);opacity:0.6;">
    💡 Ctrl+clic pour sélectionner plusieurs dates → créer des shifts en lot
  </div>`;
}

// ---- Multi-select & row management functions ----

function schedAddRow(trainerId) {
  if (!window._schedExtraRows) window._schedExtraRows = {};
  const existing = window._schedExtraRows[trainerId] || [];
  // Cycle through: soir → weekend → soir+weekend
  let next = 'soir';
  if (existing.includes('soir') && !existing.includes('weekend')) next = 'weekend';
  else if (existing.includes('soir') && existing.includes('weekend')) {
    // Already have both — do nothing
    return;
  }
  window._schedExtraRows[trainerId] = [...existing, next];
  renderSchedule(document.getElementById('content'), document.getElementById('controls'));
}

function schedCellClick(entryId, trainerId, dateStr, quart, event) {
  if (event && event.ctrlKey) {
    // Multi-select mode
    const selKey = `${trainerId}|${dateStr}|${quart}`;
    // Lock to same trainer
    if (_schedSelTrainer && _schedSelTrainer !== trainerId) return;
    _schedSelTrainer = trainerId;
    if (_schedSelection[selKey]) {
      delete _schedSelection[selKey];
      if (Object.keys(_schedSelection).length === 0) _schedSelTrainer = null;
    } else {
      _schedSelection[selKey] = { trainerId, dateStr, quart };
    }
    // Re-render to show selection highlights
    renderSchedule(document.getElementById('content'), document.getElementById('controls'));
    return;
  }
  // Normal click
  _schedSelection = {};
  _schedSelTrainer = null;
  if (entryId) {
    schedOpenPopup(entryId, event);
  } else {
    schedClickEmpty(trainerId, dateStr, quart);
  }
}

function schedCreateBulkShifts() {
  const selected = Object.values(_schedSelection);
  if (!selected.length) return;
  const trainer = selected[0].trainerId;
  const dates = selected.map(s => s.dateStr).sort();
  // Open modal prefilled with trainer + first date, dates list shown
  _schedModalEntry = null;
  _schedModalPrefill = {
    instructor_id: trainer,
    date: dates[0],
    _bulkDates: dates,
    quart: selected[0].quart || ''
  };
  schedRenderModal();
}

function schedClearSelection() {
  _schedSelection = {};
  _schedSelTrainer = null;
  renderSchedule(document.getElementById('content'), document.getElementById('controls'));
}

// ---- VIEW 2: Hebdomadaire ----

function schedGetWeekStart(year, month) {
  // Return Monday of current week based on _schedMonth/_schedYear — use first week that has the 1st
  const firstDay = new Date(year, month - 1, 1);
  const dow = firstDay.getDay();
  const diff = dow === 0 ? -6 : 1 - dow;
  const monday = new Date(firstDay);
  monday.setDate(firstDay.getDate() + diff);
  return monday;
}

function schedBuildWeekView() {
  // Use _schedWeekStart if set, else compute from month
  const weekStart = _schedWeekStart || schedGetWeekStart(_schedYear, _schedMonth);
  const todayS = schedTodayStr();

  // Build 7 days
  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    weekDays.push(d.toISOString().slice(0, 10));
  }

  const entries = _schedProgram
    ? _schedEntries.filter(e => e.program === _schedProgram)
    : _schedEntries;

  // Filter entries to week
  const weekEntries = entries.filter(e => weekDays.includes(e.date));

  // Group by date
  const byDate = {};
  weekEntries.forEach(e => {
    if (!byDate[e.date]) byDate[e.date] = [];
    byDate[e.date].push(e);
  });

  // Hours 8–22
  const hours = [];
  for (let h = 8; h <= 22; h++) hours.push(h);

  // Header
  let headerHTML = `<th class="time-col">Heure</th>`;
  weekDays.forEach((d, i) => {
    const isToday = d === todayS;
    const dayD = new Date(d + 'T00:00:00');
    headerHTML += `<th${isToday ? ' style="color:var(--a);background:rgba(255,107,53,0.1);"' : ''}>
      <div style="font-size:9px;color:var(--td);text-transform:uppercase;">${SCHED_DAYS_FR[i]}</div>
      <div style="font-size:12px;font-weight:700;">${dayD.getDate()} ${SCHED_MONTHS_FR[dayD.getMonth()].slice(0,3)}</div>
    </th>`;
  });

  // Body: for each hour, each day
  let bodyHTML = '';
  hours.forEach(h => {
    const hStr = String(h).padStart(2, '0') + ':00';
    bodyHTML += `<tr>`;
    bodyHTML += `<td class="time-cell">${hStr}</td>`;
    weekDays.forEach(dateS => {
      const isToday = dateS === todayS;
      const dayEntries = (byDate[dateS] || []).filter(e => {
        const st = parseInt((e.start_time || '09:00').split(':')[0]);
        return st === h;
      });
      const pills = dayEntries.map(e => {
        const color = schedProgramColor(e.program);
        const trainer = data.find(p => p.id === e.instructor_id);
        const label = (trainer ? trainer.name.split(' ')[0] : '') + ' ' + schedCellContent(e);
        return `<span class="sched-week-pill" style="background:${color};"
          onclick="schedOpenPopup('${esc(e.id)}', event); event.stopPropagation();"
          title="${esc(label)} ${esc(e.start_time||'')}–${esc(e.end_time||'')}">${esc(label.trim())}</span>`;
      }).join('');
      bodyHTML += `<td class="${isToday ? 'sched-today-col' : ''}"
        onclick="schedClickEmpty('','${esc(dateS)}','')">
        ${pills}
      </td>`;
    });
    bodyHTML += `</tr>`;
  });

  // Week nav label
  const endDay = new Date(weekStart);
  endDay.setDate(weekStart.getDate() + 6);
  const sm = SCHED_MONTHS_FR[weekStart.getMonth()];
  const em = SCHED_MONTHS_FR[endDay.getMonth()];
  const weekLabel = weekStart.getDate() + ' ' + sm + ' – ' + endDay.getDate() + ' ' + em + ' ' + endDay.getFullYear();

  return `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
      <button class="btn" onclick="schedNavWeek(-1)">&#8592;</button>
      <span style="font-size:13px;font-weight:600;">${esc(weekLabel)}</span>
      <button class="btn" onclick="schedNavWeek(1)">&#8594;</button>
    </div>
    <div class="sched-week-wrap">
      <table class="sched-week-grid">
        <thead><tr>${headerHTML}</tr></thead>
        <tbody>${bodyHTML}</tbody>
      </table>
    </div>`;
}

// ---- VIEW 3: Par trainer ----

function schedBuildTrainerView() {
  const trainers = schedGetTrainers();

  // Sidebar
  let sidebarHTML = `<div class="sched-trainer-sidebar">
    <div class="sched-trainer-sidebar-title">Formateurs</div>`;
  trainers.forEach(t => {
    const col = avatarColor(t.id);
    const ini = initials(t.name);
    const active = _schedTrainer === t.id;
    sidebarHTML += `<div class="sched-trainer-item${active ? ' active' : ''}" onclick="schedSelectTrainer('${esc(t.id)}')">
      <div style="width:24px;height:24px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
      <span class="sched-trainer-name">${esc(t.name)}</span>
    </div>`;
  });
  sidebarHTML += `</div>`;

  // Main content
  let mainHTML = '';
  if (!_schedTrainer) {
    mainHTML = `<div class="hor-empty-state" style="display:flex;align-items:center;justify-content:center;min-height:200px;">
      Sélectionnez un formateur dans la liste à gauche.
    </div>`;
  } else {
    const trainer = data.find(p => p.id === _schedTrainer);
    if (!trainer) {
      mainHTML = `<div class="hor-empty-state">Formateur introuvable.</div>`;
    } else {
      const col = avatarColor(trainer.id);
      const ini = initials(trainer.name);

      // Header
      mainHTML += `<div class="sched-trainer-header">
        <div style="width:40px;height:40px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <div>
          <div style="font-size:15px;font-weight:700;">${esc(trainer.name)}</div>
          <div style="font-size:11px;color:var(--td);">${esc(trainer.role || '')}</div>
        </div>
      </div>`;

      // Filter entries for this trainer
      const tEntries = _schedEntries.filter(e => e.instructor_id === _schedTrainer);

      if (!tEntries.length) {
        mainHTML += `<div class="hor-empty-state">Aucun shift ce mois-ci pour ${esc(trainer.name)}.</div>`;
      } else {
        // Session IDs list
        const withSession = tEntries.filter(e => e.session_id);
        const sessionListHTML = withSession.length
          ? withSession.map(e => `
            <div class="sched-session-row">
              <span class="sched-session-date">${esc(e.date)}</span>
              <span class="sched-session-prog" style="color:${schedProgramColor(e.program)};">${esc(schedProgramLabel(e.program))}</span>
              <span class="sched-session-id" onclick="schedCopySessionId('${esc(e.session_id)}')" title="Cliquer pour copier">${esc(e.session_id)}</span>
            </div>`)
            .join('')
          : `<div style="font-size:11px;color:var(--td);padding:8px 0;">Aucun session ID généré (les nouveaux shifts en auront un).</div>`;

        mainHTML += `<div class="sched-session-list">
          <div class="sched-session-list-title">
            <span>Session IDs — ${esc(schedMonthLabel())}</span>
            <button class="btn" style="font-size:10px;padding:3px 10px;" onclick="schedExportSessions()">Exporter pour facture</button>
          </div>
          ${sessionListHTML}
        </div>`;

        // Mini calendar for the month
        const days = schedDaysInMonth(_schedMonth, _schedYear);
        const entryByDate = {};
        tEntries.forEach(e => {
          if (!entryByDate[e.date]) entryByDate[e.date] = [];
          entryByDate[e.date].push(e);
        });

        let calHTML = `<div style="font-size:13px;font-weight:700;margin-bottom:8px;">${esc(schedMonthLabel())}</div>
          <div style="overflow-x:auto;">
          <table style="border-collapse:collapse;min-width:100%;">
            <thead><tr>`;
        SCHED_DAYS_FR.forEach(d => {
          calHTML += `<th style="background:var(--sh);border:1px solid var(--b);padding:6px 8px;font-size:10px;font-weight:600;color:var(--td);text-align:center;">${d}</th>`;
        });
        calHTML += `</tr></thead><tbody><tr>`;

        const firstDow = schedDayOfWeek(schedDateStr(_schedYear, _schedMonth, 1));
        let col2 = 0;
        for (let i = 0; i < firstDow; i++) {
          calHTML += `<td style="background:var(--bg);border:1px solid var(--b);height:64px;"></td>`;
          col2++;
        }

        const todayS = schedTodayStr();
        for (let d = 1; d <= days; d++) {
          const dateS = schedDateStr(_schedYear, _schedMonth, d);
          const isToday = dateS === todayS;
          const dayArr = entryByDate[dateS] || [];
          const pills  = dayArr.slice(0, 2).map(e => {
            const bg = schedCellBg(e) || SCHED_STATUS_COLORS[e.status] || '#60a5fa';
            return `<div style="font-size:9px;font-weight:700;padding:1px 4px;border-radius:2px;background:${bg};color:#fff;margin-bottom:2px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
              onclick="schedOpenPopup('${esc(e.id)}', event); event.stopPropagation();">${esc(schedCellContent(e))}</div>`;
          }).join('');
          const overflow = dayArr.length > 2 ? `<div style="font-size:8px;color:var(--td);">+${dayArr.length - 2}</div>` : '';

          calHTML += `<td style="border:1px solid var(--b);padding:4px;vertical-align:top;min-height:64px;height:64px;background:${isToday ? 'rgba(255,107,53,0.06)' : 'var(--s)'};cursor:pointer;"
            onclick="schedClickEmpty('${esc(_schedTrainer)}','${esc(dateS)}','')">
            <div style="font-size:10px;font-weight:700;color:${isToday ? 'var(--a)' : 'var(--td)'};margin-bottom:3px;">${d}</div>
            ${pills}${overflow}
          </td>`;
          col2++;

          if (col2 % 7 === 0 && d < days) calHTML += `</tr><tr>`;
        }

        // Pad remaining
        const rem = 7 - (col2 % 7 === 0 ? 0 : col2 % 7);
        if (rem < 7) {
          for (let i = 0; i < rem; i++) {
            calHTML += `<td style="background:var(--bg);border:1px solid var(--b);height:64px;"></td>`;
          }
        }
        calHTML += `</tr></tbody></table></div>`;

        mainHTML += `<div style="background:var(--s);border:1px solid var(--b);border-radius:10px;padding:14px 18px;">${calHTML}</div>`;
      }
    }
  }

  return `<div class="sched-trainer-layout">
    ${sidebarHTML}
    <div class="sched-trainer-main">${mainHTML}</div>
  </div>`;
}

// ---- Shift Detail Popup ----

function schedOpenPopup(entryId, ev) {
  schedClosePopup();
  const entry = _schedEntries.find(e => e.id === entryId);
  if (!entry) return;

  const trainer = data.find(p => p.id === entry.instructor_id);
  const trainerName = trainer ? trainer.name : entry.instructor_id;
  const program  = schedProgramLabel(entry.program);
  const color    = schedProgramColor(entry.program);
  const cohort   = (entry.cohorts && entry.cohorts.code) || entry.excel_cell_code || '—';
  const location = entry.locations ? (entry.locations.name || entry.locations.city || '—') : '—';
  const status   = SCHED_STATUS_LABELS[entry.status] || entry.status || '—';
  const quart    = entry.quart || '—';
  const sessionId = entry.session_id || '—';

  const popup = document.createElement('div');
  popup.className = 'shift-popup';
  popup.id = 'shift-detail-popup';
  popup.innerHTML = `
    <div class="sp-header">
      <strong style="font-size:13px;">${esc(trainerName)}</strong>
      <button onclick="schedClosePopup()" style="background:none;border:none;color:var(--td);font-size:18px;cursor:pointer;line-height:1;padding:0;">✕</button>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
      <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block;flex-shrink:0;"></span>
      <span style="font-size:12px;font-weight:600;">${esc(program)}</span>
    </div>
    <div style="font-size:11px;color:var(--td);margin-bottom:4px;">${esc(entry.date)} · ${esc(quart)}</div>
    <div style="font-size:11px;margin-bottom:4px;"><span style="color:var(--td);">Cohorte:</span> <strong>${esc(cohort)}</strong></div>
    <div style="font-size:11px;margin-bottom:4px;"><span style="color:var(--td);">Salle:</span> ${esc(location)}</div>
    <div style="font-size:11px;margin-bottom:8px;"><span style="color:var(--td);">Statut:</span>
      <span style="background:${SCHED_STATUS_COLORS[entry.status]||'#374151'};color:#fff;font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;font-family:'Space Mono',monospace;">${esc(status)}</span>
    </div>
    ${entry.session_id ? `<div class="sp-session" onclick="schedCopySessionId('${esc(entry.session_id)}')" title="Cliquer pour copier">&#128203; ${esc(sessionId)}</div>` : ''}
    ${entry.notes ? `<div style="font-size:11px;color:var(--td);margin-top:8px;font-style:italic;">${esc(entry.notes)}</div>` : ''}
    <div style="display:flex;gap:6px;margin-top:12px;">
      <button class="btn" style="font-size:11px;padding:5px 10px;flex:1;" onclick="schedEditEntry('${esc(entryId)}')">Modifier</button>
      <button class="btn danger" style="font-size:11px;padding:5px 10px;" onclick="schedDeleteEntry('${esc(entryId)}')">Supprimer</button>
    </div>`;

  document.body.appendChild(popup);

  // Position popup near click
  if (ev) {
    const rect = popup.getBoundingClientRect();
    let x = ev.clientX + 10;
    let y = ev.clientY + 10;
    const vpW = window.innerWidth;
    const vpH = window.innerHeight;
    if (x + 320 > vpW) x = ev.clientX - 330;
    if (y + 380 > vpH) y = ev.clientY - 300;
    popup.style.left = Math.max(8, x) + 'px';
    popup.style.top  = Math.max(8, y) + 'px';
  } else {
    popup.style.left = '50%';
    popup.style.top  = '50%';
    popup.style.transform = 'translate(-50%,-50%)';
  }

  // Close on outside click
  setTimeout(() => {
    document.addEventListener('click', schedPopupOutsideClick, { once: true });
  }, 50);
}

function schedPopupOutsideClick(e) {
  const popup = document.getElementById('shift-detail-popup');
  if (popup && !popup.contains(e.target)) schedClosePopup();
}

function schedClosePopup() {
  const p = document.getElementById('shift-detail-popup');
  if (p) p.remove();
}

function schedCopySessionId(sid) {
  navigator.clipboard.writeText(sid).then(() => {
    schedFlash('Session ID copié: ' + sid);
  }).catch(() => {
    prompt('Session ID:', sid);
  });
}

function schedExportSessions() {
  const tEntries = _schedEntries.filter(e => e.instructor_id === _schedTrainer && e.session_id);
  if (!tEntries.length) { schedFlash('Aucun session ID à exporter.', true); return; }
  const lines = tEntries.map(e => e.session_id).join('\n');
  navigator.clipboard.writeText(lines).then(() => {
    schedFlash(tEntries.length + ' session ID(s) copiés pour facture');
  }).catch(() => {
    prompt('Session IDs (copier):', lines);
  });
}

// ---- Shift Modal ----

async function schedOpenNewShift(prefill) {
  _schedModalEntry   = null;
  _schedModalPrefill = prefill || {};
  await schedRenderModal();
}

async function schedEditEntry(entryId) {
  schedClosePopup();
  const entry = _schedEntries.find(e => e.id === entryId);
  if (!entry) return;
  _schedModalEntry   = entry;
  _schedModalPrefill = {};
  await schedRenderModal();
}

async function schedRenderModal() {
  const existing = document.getElementById('shift-modal-overlay');
  if (existing) existing.remove();

  // Load cohorts if needed
  let cohorts = [];
  try { cohorts = await dbGetCohorts(); } catch(e) { cohorts = []; }

  const trainers = schedGetTrainers();
  const isEdit   = !!_schedModalEntry;
  const e        = _schedModalEntry || {};
  const pf       = _schedModalPrefill;

  const trainerOpts = trainers.map(t =>
    `<option value="${esc(t.id)}"${(e.instructor_id || pf.instructor_id) === t.id ? ' selected' : ''}>${esc(t.name)}</option>`
  ).join('');

  const programs = _schedPrograms.length ? _schedPrograms : Object.entries(SCHED_DEFAULT_PROGRAM_COLORS).map(([id]) => ({ id, label: id }));
  const programOpts = programs.map(p =>
    `<option value="${esc(p.id)}"${(e.program || pf.program) === p.id ? ' selected' : ''}>${esc(p.label || p.id)}</option>`
  ).join('');

  const locationOpts = _schedLocations.length
    ? _schedLocations.map(l => `<option value="${esc(l.id)}"${e.location_id === l.id ? ' selected' : ''}>${esc(l.name || l.city || l.code)}</option>`).join('')
    : '<option value="">— Aucune salle —</option>';

  const cohortOpts = cohorts.map(c =>
    `<option value="${esc(c.id)}"${e.cohort_id === c.id ? ' selected' : ''}>${esc(c.code || c.id)}</option>`
  ).join('');

  const statusOpts = Object.entries(SCHED_STATUS_LABELS).map(([v, l]) =>
    `<option value="${v}"${(e.status || 'scheduled') === v ? ' selected' : ''}>${l}</option>`
  ).join('');

  const quartOpts = ['Jour','Soir','Weekend'].map(q =>
    `<option value="${q.toLowerCase()}"${(e.quart || pf.quart || 'jour') === q.toLowerCase() ? ' selected' : ''}>${q}</option>`
  ).join('');

  const overlay = document.createElement('div');
  overlay.id = 'shift-modal-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:2000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
  overlay.addEventListener('click', ev => { if (ev.target === overlay) schedCloseModal(); });

  const bulkDates = pf._bulkDates || null;
  const bulkBanner = bulkDates && bulkDates.length > 1 ? `
    <div style="padding:10px 20px;background:rgba(255,107,53,0.08);border-bottom:1px solid var(--b);">
      <div style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--a);margin-bottom:5px;">${bulkDates.length} dates sélectionnées</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;">${bulkDates.map(d => `<span style="font-family:'Space Mono',monospace;font-size:10px;background:rgba(255,107,53,0.15);color:var(--a);padding:2px 7px;border-radius:4px;">${d}</span>`).join('')}</div>
      <div style="font-size:11px;color:var(--td);margin-top:6px;">Un shift sera créé pour chaque date ci-dessus avec les mêmes paramètres.</div>
    </div>` : '';

  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:14px;width:500px;max-width:95vw;max-height:90vh;overflow-y:auto;display:flex;flex-direction:column;">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;border-bottom:1px solid var(--b);">
        <h3 style="font-size:16px;font-weight:700;">${isEdit ? 'Modifier le shift' : bulkDates && bulkDates.length > 1 ? `Créer ${bulkDates.length} shifts` : 'Nouveau shift'}</h3>
        <button onclick="schedCloseModal()" style="background:none;border:none;color:var(--td);font-size:18px;cursor:pointer;padding:0 4px;line-height:1;">✕</button>
      </div>
      ${bulkBanner}
      <div style="padding:16px 20px;display:flex;flex-direction:column;gap:12px;">
        <div class="sched-form-grid">
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Formateur</label>
            <select id="sm_instructor" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;">
              ${trainerOpts}
            </select>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Date</label>
            <input type="date" id="sm_date" value="${e.date || pf.date || ''}" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Quart</label>
            <select id="sm_quart" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;">
              ${quartOpts}
            </select>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Programme</label>
            <select id="sm_program" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;">
              ${programOpts}
            </select>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Cohorte</label>
            <input type="text" id="sm_cohort_text" placeholder="ex: JL57" value="${esc((e.cohorts && e.cohorts.code) || e.excel_cell_code || pf.cohort_code || '')}" list="sm_cohort_list" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;"/>
            <datalist id="sm_cohort_list">${cohortOpts}</datalist>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Salle</label>
            <select id="sm_location" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;">
              <option value="">— Aucune salle —</option>
              ${locationOpts}
            </select>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Heure début</label>
            <input type="time" id="sm_start" value="${e.start_time || '09:00'}" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Heure fin</label>
            <input type="time" id="sm_end" value="${e.end_time || '17:00'}" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Statut</label>
            <select id="sm_status" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;">
              ${statusOpts}
            </select>
          </div>
          ${isEdit && e.session_id ? `<div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Session ID</label>
            <div style="font-family:'Space Mono',monospace;font-size:10px;background:rgba(255,107,53,0.1);color:var(--a);padding:8px 10px;border-radius:6px;word-break:break-all;">${esc(e.session_id)}</div>
          </div>` : ''}
          <div class="full-width">
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Notes</label>
            <textarea id="sm_notes" placeholder="Notes facultatives..." style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;font-size:13px;outline:none;resize:vertical;min-height:50px;">${esc(e.notes || '')}</textarea>
          </div>
        </div>
      </div>
      <div style="padding:14px 20px;border-top:1px solid var(--b);display:flex;align-items:center;justify-content:space-between;">
        ${isEdit ? `<button class="btn danger" style="font-size:12px;" onclick="schedDeleteEntry('${esc(e.id)}')">Supprimer</button>` : '<span></span>'}
        <div style="display:flex;gap:8px;">
          <button class="btn" onclick="schedCloseModal()">Annuler</button>
          <button class="btn primary" id="sm_save_btn" onclick="schedSaveEntry()">Enregistrer</button>
        </div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

function schedCloseModal() {
  const o = document.getElementById('shift-modal-overlay');
  if (o) o.remove();
}

async function schedSaveEntry() {
  const gv = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };

  const instructor_id  = gv('sm_instructor');
  const date           = gv('sm_date');
  const quart          = gv('sm_quart') || null;
  const program        = gv('sm_program');
  const cohort_text    = gv('sm_cohort_text') || null;
  const location_id    = gv('sm_location') || null;
  const start_time     = gv('sm_start') || '09:00';
  const end_time       = gv('sm_end')   || '17:00';
  const status         = gv('sm_status') || 'scheduled';
  const notes          = gv('sm_notes') || null;

  if (!instructor_id) { alert('Veuillez sélectionner un formateur.'); return; }
  if (!date)          { alert('Veuillez choisir une date.');           return; }

  const payload = {
    instructor_id, date, quart, program,
    excel_cell_code: cohort_text,
    location_id, start_time, end_time,
    status, notes
  };

  const saveBtn = document.getElementById('sm_save_btn');
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Enregistrement...'; }

  // Check for bulk dates (multi-select Ctrl+click)
  const bulkDates = _schedModalPrefill && _schedModalPrefill._bulkDates;

  try {
    if (_schedModalEntry) {
      // Edit mode — update single entry
      await dbUpdateScheduleEntry(_schedModalEntry.id, payload);
      schedCloseModal();
      await schedReloadEntries();
      schedFlash('Shift mis à jour');
    } else if (bulkDates && bulkDates.length > 1) {
      // Bulk create — one entry per selected date
      const results = await Promise.allSettled(
        bulkDates.map(d => dbSaveScheduleEntry({ ...payload, date: d }))
      );
      const failed = results.filter(r => r.status === 'rejected');
      schedCloseModal();
      _schedSelection = {};
      _schedSelTrainer = null;
      await schedReloadEntries();
      if (failed.length) {
        schedFlash(`${bulkDates.length - failed.length}/${bulkDates.length} shifts créés (${failed.length} erreur${failed.length > 1 ? 's' : ''})`, true);
      } else {
        schedFlash(`${bulkDates.length} shifts créés`);
      }
    } else {
      // Single new entry
      await dbSaveScheduleEntry(payload);
      schedCloseModal();
      await schedReloadEntries();
      schedFlash('Shift enregistré');
    }
  } catch(err) {
    console.error('schedSaveEntry error:', err);
    alert('Erreur lors de la sauvegarde: ' + (err.message || err));
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Enregistrer'; }
  }
}

async function schedDeleteEntry(entryId) {
  schedClosePopup();
  if (!confirm('Supprimer ce shift? Cette action est irréversible.')) return;
  try {
    schedCloseModal();
    await dbDeleteScheduleEntry(entryId);
    await schedReloadEntries();
    schedFlash('Shift supprimé', true);
  } catch(err) {
    console.error('schedDeleteEntry error:', err);
    alert('Erreur: ' + (err.message || err));
  }
}

// ---- Empty cell click ----

function schedClickEmpty(trainerId, dateStr, quart) {
  schedClosePopup();
  schedOpenNewShift({
    instructor_id: trainerId || '',
    date: dateStr,
    quart: quart || 'jour'
  });
}

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
  // Initialize week start
  if (!_schedWeekStart) _schedWeekStart = schedGetWeekStart(_schedYear, _schedMonth);

  // Build trainer dropdown options
  const trainers = schedGetTrainers();
  const trainerFilterOpts = `<option value="">Tous les formateurs</option>` +
    trainers.map(t => `<option value="${esc(t.id)}"${_schedTrainer === t.id ? ' selected' : ''}>${esc(t.name)}</option>`).join('');

  // Build program dropdown options
  const programs = _schedPrograms.length ? _schedPrograms : Object.entries(SCHED_DEFAULT_PROGRAM_COLORS).map(([id]) => ({ id, label: id }));
  const programFilterOpts = `<option value="">Tous les programmes</option>` +
    programs.map(p => `<option value="${esc(p.id)}"${_schedProgram === p.id ? ' selected' : ''}>${esc(p.label || p.id)}</option>`).join('');

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

      <button class="btn primary" style="margin-left:auto;font-size:12px;" onclick="schedOpenNewShift({})">+ Nouveau shift</button>
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
