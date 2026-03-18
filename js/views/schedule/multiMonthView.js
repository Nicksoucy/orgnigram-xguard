// ==================== SCHEDULE: MULTI-MONTH VIEW ====================

let _schedMultiMonthCount = 4;
let _schedMultiMonthCache = {};
let _mmDragActive = false;

document.addEventListener('mouseup', () => { _mmDragActive = false; });

async function schedMultiMonthLoad() {
  const fetches = [];
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key = y + '-' + String(m).padStart(2, '0');
    if (!_schedMultiMonthCache[key]) {
      const cm = m, cy = y;
      fetches.push(
        dbGetScheduleEntries(cm, cy).then(e => { _schedMultiMonthCache[key] = e; })
                                    .catch(() => { _schedMultiMonthCache[key] = []; })
      );
    }
    m++; if (m > 12) { m = 1; y++; }
  }
  if (fetches.length) await Promise.all(fetches);
}

function schedMultiMonthInvalidate() { _schedMultiMonthCache = {}; }

// ─── Drag-select handlers ─────────────────────────────────────────────────────

function mmCellMouseDown(trainerId, dateStr, quart, event) {
  event.preventDefault();
  if (_schedSelTrainer && _schedSelTrainer !== trainerId) schedClearSelection();
  _schedSelTrainer = trainerId;
  _mmDragActive    = true;

  const key = trainerId + '|' + dateStr + '|' + quart;
  if (_schedSelection[key]) {
    delete _schedSelection[key];
    if (!Object.keys(_schedSelection).length) _schedSelTrainer = null;
  } else {
    _schedSelection[key] = { trainerId, dateStr, quart };
  }
  _mmSyncSelUI();
  _schedUpdateToolbar();
}

function mmCellMouseOver(trainerId, dateStr, quart, event) {
  if (!_mmDragActive) return;
  if (_schedSelTrainer && _schedSelTrainer !== trainerId) return;
  const key = trainerId + '|' + dateStr + '|' + quart;
  if (!_schedSelection[key]) {
    _schedSelection[key] = { trainerId, dateStr, quart };
    event.currentTarget.classList.add('mm-selected');
    _schedUpdateToolbar();
  }
}

function _mmSyncSelUI() {
  document.querySelectorAll('.mm-cell[data-mmkey]').forEach(td => {
    td.classList.toggle('mm-selected', !!_schedSelection[td.dataset.mmkey]);
  });
  _schedUpdateToolbar();
}

// ─── Main builder ─────────────────────────────────────────────────────────────

function schedBuildMultiMonthView() {
  const todayS     = schedTodayStr();
  const allTrainers = schedGetOrderedTrainers();
  const trainers   = _schedTrainer
    ? allTrainers.filter(t => t.id === _schedTrainer)
    : allTrainers;

  if (!trainers.length)
    return `<div class="hor-empty-state">Aucun formateur trouvé. Ajustez le filtre.</div>`;

  const selCount = Object.keys(_schedSelection).length;
  const selToolbar = `
    <div id="sched-sel-toolbar" style="position:sticky;top:0;z-index:20;background:rgba(255,107,53,0.15);border:1px solid var(--a);border-radius:8px;padding:8px 14px;margin-bottom:12px;display:${selCount>0?'flex':'none'};align-items:center;gap:12px;flex-wrap:wrap;">
      <span class="sel-count" style="color:var(--a);font-weight:700;">✓ ${selCount} date${selCount>1?'s':''} sélectionnée${selCount>1?'s':''}</span>
      <span class="sel-dates" style="color:var(--td);font-size:12px;">${Object.values(_schedSelection).map(s=>s.dateStr).sort().join(', ')}</span>
      <button class="sel-create-btn" onclick="schedCreateBulkShifts()" style="margin-left:auto;background:var(--a);color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-weight:700;">Créer ${selCount} shift${selCount>1?'s':''}</button>
      <button onclick="schedClearSelection()" style="background:var(--s);color:var(--td);border:1px solid var(--b);border-radius:6px;padding:6px 10px;cursor:pointer;">✕</button>
    </div>`;

  let blocks = '';
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key  = y + '-' + String(m).padStart(2, '0');
    let entries = _schedMultiMonthCache[key] || [];
    if (_schedProgram) entries = entries.filter(e => e.program === _schedProgram);

    // Index: instructor_id → quart → date → [entries]
    const byTQD = {};
    entries.forEach(e => {
      const q = e.quart || 'jour';
      if (!byTQD[e.instructor_id]) byTQD[e.instructor_id] = {};
      if (!byTQD[e.instructor_id][q]) byTQD[e.instructor_id][q] = {};
      if (!byTQD[e.instructor_id][q][e.date]) byTQD[e.instructor_id][q][e.date] = [];
      byTQD[e.instructor_id][q][e.date].push(e);
    });

    // Which quarts exist globally this month (preserve canonical order)
    const QUART_ORDER = ['jour', 'soir', 'weekend'];
    const activeQuarts = QUART_ORDER.filter(q =>
      trainers.some(t => byTQD[t.id] && byTQD[t.id][q])
    );
    // Always show at least one row
    const quartsToShow = activeQuarts.length ? activeQuarts : ['jour'];

    const holidays = schedGetHolidaysQC(y);
    schedGetHolidaysQC(y + 1).forEach(h => holidays.add(h));

    blocks += _mmBlock(m, y, SCHED_MONTHS_FR[m-1]+' '+y, schedDaysInMonth(m,y),
                       trainers, byTQD, quartsToShow, holidays, todayS);
    m++; if (m > 12) { m = 1; y++; }
  }

  return `${selToolbar}
    <div class="mm-stack-wrap">${blocks}</div>
    <div style="margin-top:8px;font-size:11px;color:var(--td);opacity:0.6;">
      💡 Clic ou glisser pour sélectionner des dates → créer des shifts en lot
    </div>`;
}

// ─── One month block ──────────────────────────────────────────────────────────

function _mmBlock(month, year, label, days, trainers, byTQD, quartsToShow, holidays, todayS) {

  // ── Day header ──
  let headerCells = `<th class="mm-name-col" colspan="2">Formateur</th>`;
  for (let d = 1; d <= days; d++) {
    const dateS   = schedDateStr(year, month, d);
    const isToday = dateS === todayS;
    const isWe    = schedIsWeekend(year, month, d);
    const isHol   = holidays.has(dateS);
    const dow     = SCHED_DAYS_FR[schedDayOfWeek(dateS)];
    const weCls   = isWe && !isHol ? ' mm-we-col' : '';
    const style   = isToday ? 'color:var(--a);background:rgba(255,107,53,0.18);'
      : isHol ? 'color:#93c5fd;background:rgba(147,197,253,0.14);'
      : '';
    headerCells += `<th class="mm-day-th${weCls}" style="${style}" title="${isHol?'Jour férié':dateS}">
      <div style="font-size:8px;line-height:1.1;">${isHol?'🏖':dow}</div>
      <div style="font-size:11px;font-weight:700;line-height:1.2;">${d}</div>
    </th>`;
  }

  // ── Body: one row per trainer × quart ──
  const QUART_LABELS = { jour: 'Jour', soir: 'Soir', weekend: 'WE' };

  let bodyRows = '';
  trainers.forEach(trainer => {
    const col  = avatarColor(trainer.id);
    const ini  = initials(trainer.name);
    const name = trainer.name.split(' ').slice(0, 2).join(' ');
    const tid  = esc(trainer.id);
    const tQuartData = byTQD[trainer.id] || {};

    quartsToShow.forEach((quart, qi) => {
      const isFirstRow = qi === 0;
      const isLastRow  = qi === quartsToShow.length - 1;
      const quartData  = tQuartData[quart] || {};

      let row = `<tr class="${isLastRow ? 'mm-trainer-last' : ''}">`;

      // ── Name cell: only on first quart row, rowspan covers all quarts ──
      if (isFirstRow) {
        row += `<td class="mm-name-col mm-name-cell" rowspan="${quartsToShow.length}">
          <div style="display:flex;align-items:center;gap:5px;">
            <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
            <span style="font-size:11px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(name)}</span>
          </div>
        </td>`;
      }

      // ── Quart label cell ──
      row += `<td class="mm-quart-label${isLastRow ? ' mm-quart-last' : ''}">${QUART_LABELS[quart] || quart}</td>`;

      // ── Day cells ──
      for (let d = 1; d <= days; d++) {
        const dateS      = schedDateStr(year, month, d);
        const escapedDate = esc(dateS);
        const isToday    = dateS === todayS;
        const isWe       = schedIsWeekend(year, month, d);
        const isHol      = holidays.has(dateS);
        const dayEntries = quartData[dateS] || [];
        const mmKey      = trainer.id + '|' + dateS + '|' + quart;
        const isSel      = !!_schedSelection[mmKey];
        const dimmed     = isWe || isHol;

        const weBodyCls = isWe && !isHol ? ' mm-we-col' : '';
        const bg = isToday ? 'background:rgba(255,107,53,0.10);'
          : isHol ? 'background:rgba(147,197,253,0.10);'
          : '';

        const dragAttrs = !dimmed
          ? ` data-mmkey="${esc(mmKey)}" onmousedown="mmCellMouseDown('${tid}','${escapedDate}','${quart}',event)" onmouseover="mmCellMouseOver('${tid}','${escapedDate}','${quart}',event)"`
          : '';

        const selClass = isSel ? ' mm-selected' : '';
        const lastCls  = isLastRow ? ' mm-cell-last' : '';

        if (dayEntries.length === 0) {
          const cls = dimmed ? 'mm-dim' : 'mm-empty';
          row += `<td class="mm-cell ${cls}${weBodyCls}${selClass}${lastCls}" style="${bg}"${dragAttrs}></td>`;
        } else {
          const chips = dayEntries.map(e => {
            const chipBg = schedCellBg(e) || '#3b82f6';
            const lbl    = _mmLabel(e);
            const tip    = schedCellTooltip(e);
            return `<span class="mm-chip" style="background:${chipBg};" title="${esc(tip)}"
              onclick="schedOpenPopup('${esc(e.id)}',null)">${esc(lbl)}</span>`;
          }).join('');
          row += `<td class="mm-cell${weBodyCls}${selClass}${lastCls}" style="${bg}"${dragAttrs}>${chips}</td>`;
        }
      }

      row += `</tr>`;
      bodyRows += row;
    });
  });

  return `
    <div class="mm-block">
      <div class="mm-block-title">${esc(label)}</div>
      <div class="mm-block-scroll">
        <table class="mm-table">
          <thead><tr>${headerCells}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
    </div>`;
}

function _mmLabel(entry) {
  if (!entry) return '';
  const s = entry.status || 'scheduled';
  if (s === 'vacation')    return 'VAC';
  if (s === 'unavailable') return 'OFF';
  if (s === 'holiday')     return 'F';
  if (s === 'cancelled')   return 'X';
  if (s === 'replacement') return 'R';
  const code = entry.excel_cell_code || (entry.cohorts && entry.cohorts.code) || '';
  if (code) return code;
  return (entry.program || '?').substring(0, 5);
}
