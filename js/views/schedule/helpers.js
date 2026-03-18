// ==================== SCHEDULE: HELPERS ====================

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
  // RCR → orange
  if (entry.program === 'RCR') return '#f97316';
  const city = entry.locations && entry.locations.city;
  // Any program at Salle Québec → violet
  const isQc = entry.location_id === SCHED_LOCATION_QC || city === 'Quebec';
  if (isQc) return '#7c3aed';
  // Any program at Salle Montréal → teal
  const isMtl = city === 'Montreal';
  if (isMtl) return '#0d9488';
  return schedProgramColor(entry.program);
}

// ---- Trainer order helpers ----

function schedGetOrderedTrainers() {
  const all = schedGetTrainers();
  if (!_schedTrainerOrder || !_schedTrainerOrder.length) return all;
  // Sort by saved order, append any new trainers at the end
  const ordered = [];
  _schedTrainerOrder.forEach(id => {
    const t = all.find(x => x.id === id);
    if (t) ordered.push(t);
  });
  all.forEach(t => { if (!ordered.find(x => x.id === t.id)) ordered.push(t); });
  return ordered;
}

// ---- Dropdown option builders (DRY helpers) ----

function schedGetPrograms() {
  return _schedPrograms.length
    ? _schedPrograms
    : Object.entries(SCHED_DEFAULT_PROGRAM_COLORS).map(([id]) => ({ id, label: id }));
}

function schedBuildProgramOpts(selectedId) {
  return schedGetPrograms().map(p =>
    `<option value="${esc(p.id)}"${selectedId === p.id ? ' selected' : ''}>${esc(p.label || p.id)}</option>`
  ).join('');
}

function schedBuildLocationOpts(selectedId) {
  if (!_schedLocations.length) return `<option value="">— Aucune salle —</option>`;
  return _schedLocations.map(l =>
    `<option value="${esc(l.id)}"${selectedId === l.id ? ' selected' : ''}>${esc(l.name || l.city || l.code)}</option>`
  ).join('');
}

function schedBuildTrainerOpts(selectedId) {
  return schedGetOrderedTrainers().map(t =>
    `<option value="${esc(t.id)}"${selectedId === t.id ? ' selected' : ''}>${esc(t.name)}</option>`
  ).join('');
}
