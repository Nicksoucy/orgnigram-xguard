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
  // Normal: show cohort code or excel_cell_code
  const code = (entry.cohorts && entry.cohorts.code) || entry.excel_cell_code || '';
  return code || (entry.program ? entry.program.substring(0, 4) : '?');
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

  // Determine which trainers have entries for the month
  let activeTrainers = filteredTrainers.filter(t => {
    if (_schedProgram) return entryMap[t.id] && Object.keys(entryMap[t.id]).length > 0;
    // Show all trainers who have entries OR are type trainer
    return entryMap[t.id] || t.dept === 'training' || (t.programs && t.programs.length > 0);
  });

  if (!_schedTrainer && !activeTrainers.length) {
    activeTrainers = filteredTrainers;
  }

  // Build rows: determine shift types per trainer
  const rows = [];
  activeTrainers.forEach(trainer => {
    const tEntries = entryMap[trainer.id] || {};
    let hasJour = false, hasSoir = false, hasWeekend = false;
    Object.values(tEntries).forEach(dayArr => {
      dayArr.forEach(e => {
        const q = (e.quart || '').toLowerCase();
        if (q === 'soir') hasSoir = true;
        else if (q === 'weekend') hasWeekend = true;
        else hasJour = true;
      });
    });

    const both = hasJour && hasSoir;
    if (hasJour || (!hasSoir && !hasWeekend)) {
      rows.push({ trainer, quart: both ? 'jour' : (hasSoir ? null : (hasWeekend ? null : null)), label: both ? 'jour' : null });
    }
    if (hasSoir) {
      rows.push({ trainer, quart: 'soir', label: 'soir' });
    }
    if (hasWeekend) {
      rows.push({ trainer, quart: 'weekend', label: 'weekend' });
    }
    // If no entries at all, add one default row
    if (!hasJour && !hasSoir && !hasWeekend) {
      rows.push({ trainer, quart: null, label: null });
    }
  });

  // Build day headers
  let headerHTML = `<th class="trainer-col">Formateur</th>`;
  for (let d = 1; d <= days; d++) {
    const dateS = schedDateStr(_schedYear, _schedMonth, d);
    const isToday = dateS === todayS;
    const isWe   = schedIsWeekend(_schedYear, _schedMonth, d);
    const dow    = SCHED_DAYS_FR[schedDayOfWeek(dateS)];
    headerHTML += `<th${isWe ? ' style="color:var(--td);opacity:0.7;"' : ''}${isToday ? ' style="color:var(--a);"' : ''} title="${dow} ${d}">${d}</th>`;
  }

  // Build body rows
  let bodyHTML = '';
  rows.forEach(({ trainer, quart, label }) => {
    const col = avatarColor(trainer.id);
    const ini = initials(trainer.name);
    const tEntries = entryMap[trainer.id] || {};

    bodyHTML += `<tr>`;
    bodyHTML += `<td class="trainer-name">
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <div>
          <div style="font-size:11px;font-weight:700;">${esc(trainer.name)}</div>
          ${label ? `<div class="shift-label">[${esc(label)}]</div>` : ''}
        </div>
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

      if (entry) {
        const cellText   = schedCellContent(entry);
        const cellClass  = schedCellClass(entry);
        const cellBg     = schedCellBg(entry);
        const bgStyle    = cellBg ? `background:${cellBg};color:#fff;` : '';
        bodyHTML += `<td class="${tdClass}" onclick="schedOpenPopup('${escapedId}', event)">
          <span class="sched-cell ${cellClass}" style="${bgStyle}" title="${esc(cellText)}">${esc(cellText)}</span>
        </td>`;
      } else {
        bodyHTML += `<td class="${tdClass}" onclick="schedClickEmpty('${trainerId}','${escapedDateS}','${quart || ''}')">
          <span class="sched-cell empty-cell">+</span>
        </td>`;
      }
    }

    bodyHTML += `</tr>`;
  });

  if (!rows.length) {
    return `<div class="hor-empty-state">Aucun formateur avec des shifts ce mois-ci. Cliquez sur "+ Nouveau shift" pour en ajouter.</div>`;
  }

  return `<div id="sched-wrap">
    <table class="sched-grid">
      <thead><tr>${headerHTML}</tr></thead>
      <tbody>${bodyHTML}</tbody>
    </table>
  </div>`;
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

  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:14px;width:500px;max-width:95vw;max-height:90vh;overflow-y:auto;display:flex;flex-direction:column;">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;border-bottom:1px solid var(--b);">
        <h3 style="font-size:16px;font-weight:700;">${isEdit ? 'Modifier le shift' : 'Nouveau shift'}</h3>
        <button onclick="schedCloseModal()" style="background:none;border:none;color:var(--td);font-size:18px;cursor:pointer;padding:0 4px;line-height:1;">✕</button>
      </div>
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

  try {
    if (_schedModalEntry) {
      await dbUpdateScheduleEntry(_schedModalEntry.id, payload);
    } else {
      await dbSaveScheduleEntry(payload);
    }
    schedCloseModal();
    await schedReloadEntries();
    schedFlash('Shift enregistré');
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
