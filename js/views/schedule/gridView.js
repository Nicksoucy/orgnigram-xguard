// ==================== SCHEDULE: GRID VIEW ====================

// ---- VIEW 1: Grille Mensuelle ----

function schedBuildMonthGrid() {
  const days    = schedDaysInMonth(_schedMonth, _schedYear);
  const todayS  = schedTodayStr();
  const trainers = schedGetOrderedTrainers();

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
  // Pre-compute holidays for this month
  const _holidays = schedGetHolidaysQC(_schedYear);
  schedGetHolidaysQC(_schedYear + 1).forEach(h => _holidays.add(h));

  for (let d = 1; d <= days; d++) {
    const dateS = schedDateStr(_schedYear, _schedMonth, d);
    const isToday = dateS === todayS;
    const isWe   = schedIsWeekend(_schedYear, _schedMonth, d);
    const isHoliday = _holidays.has(dateS);
    const dow    = SCHED_DAYS_FR[schedDayOfWeek(dateS)];
    const color  = isToday ? 'var(--a)' : isHoliday ? '#93c5fd' : isWe ? 'var(--td)' : 'inherit';
    const opacity = isWe && !isHoliday ? 'opacity:0.6;' : '';
    const holidayBg = isHoliday ? 'background:rgba(59,130,246,0.15);' : '';
    headerHTML += `<th style="color:${color};${opacity}${isHoliday ? 'background:rgba(147,197,253,0.25);' : ''}line-height:1.2;" title="${isHoliday ? 'Jour férié' : ''}">
      <div style="font-size:9px;font-weight:500;">${isHoliday ? '🏖' : dow}</div>
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
    const isFirstRow = !label; // only first row of trainer gets drag handle
    bodyHTML += `<tr data-trainer="${esc(trainer.id)}" data-quart="${esc(quart||'')}"
      ${isFirstRow ? `draggable="true" ondragstart="schedDragStart(event,'${esc(trainer.id)}')" ondragover="schedDragOver(event)" ondrop="schedDrop(event,'${esc(trainer.id)}')" ondragend="schedDragEnd(event)"` : ''}
      style="transition:opacity 0.15s;">`;
    bodyHTML += `<td class="trainer-name">
      <div style="display:flex;align-items:center;gap:6px;">
        ${isFirstRow ? `<div class="sched-drag-handle" title="Glisser pour réordonner" style="color:var(--td);cursor:grab;font-size:13px;flex-shrink:0;padding:0 2px;user-select:none;" onmousedown="this.style.cursor='grabbing'" onmouseup="this.style.cursor='grab'">⠿</div>` : `<div style="width:15px;flex-shrink:0;"></div>`}
        <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;${label?'cursor:pointer;':''}" ${label ? `onclick="schedOpenPatternForRow('${esc(trainer.id)}','${esc(label)}')" title="Créer des cohortes ${esc(label)}"` : ''}>${esc(trainer.name)}</div>
          ${label ? `<div class="shift-label" onclick="schedOpenPatternForRow('${esc(trainer.id)}','${esc(label)}')" title="Cliquer pour créer des cohortes pour ce quart" style="color:var(--a);font-size:9px;cursor:pointer;text-decoration:underline dotted;" onmouseover="this.style.color='var(--t)'" onmouseout="this.style.color='var(--a)'">[${esc(label)}] ✦</div>` : ''}
        </div>
        ${label ? `<button onclick="schedRemoveRow('${esc(trainer.id)}','${esc(label)}')" title="Retirer cette ligne" style="background:none;border:none;color:var(--td);cursor:pointer;font-size:13px;padding:0 2px;flex-shrink:0;line-height:1;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--td)'">−</button>` : ''}
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

      const isHoliday = _holidays.has(dateS);
      const tdClass = [isToday ? 'today' : '', isWe ? 'weekend-col' : '', isHoliday ? 'holiday-col' : ''].filter(Boolean).join(' ');
      const escapedDateS = esc(dateS);
      const trainerId    = esc(trainer.id);

      const selKey = `${trainer.id}|${dateS}|${quart||''}`;
      const isSelected = !!_schedSelection[selKey];
      const selStyle = isSelected ? 'outline:2px solid var(--a);outline-offset:-2px;' : '';

      if (matchEntries.length > 0) {
        // Stack all entries in this cell
        // Compute trainer initials using shared initials() from utils.js
        const trainerInitials = initials(trainer.name);

        const stackedHTML = matchEntries.map(entry => {
          const cellText = schedCellContent(entry);
          const cellTip  = schedCellTooltip(entry);
          const cellBg   = schedCellBg(entry);
          const bgStyle  = cellBg ? `background:${cellBg};color:#fff;` : '';
          // Show code + initials: "LS34-ME" or just program if no code
          const code = entry.excel_cell_code || '';
          const displayText = code ? `${code}-${trainerInitials}` : cellText;
          const sessionLine = entry.session_id
            ? `<div style="font-size:7px;opacity:0.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px;font-family:'Space Mono',monospace;">${esc(entry.session_id.split('-').slice(-1)[0])}</div>`
            : '';
          return `<span class="sched-cell" style="${bgStyle};display:flex;flex-direction:column;align-items:center;margin-bottom:2px;width:100%;" title="${esc(cellTip)}" onclick="schedCellClick('${esc(entry.id)}','${trainerId}','${escapedDateS}','${quart||''}',event)">
            <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">${esc(displayText)}</span>${sessionLine}
          </span>`;
        }).join('');
        bodyHTML += `<td class="${tdClass}" style="${selStyle};padding:2px;vertical-align:top;${isHoliday ? 'background:rgba(147,197,253,0.20);' : ''}">
          ${stackedHTML}
        </td>`;
      } else {
        const holidayStyle = isHoliday ? 'background:rgba(147,197,253,0.20);' : '';
        bodyHTML += `<td class="${tdClass}" style="${selStyle}${holidayStyle}" onclick="schedCellClick(null,'${trainerId}','${escapedDateS}','${quart||''}',event)">
          <span class="sched-cell empty-cell" style="${isHoliday?'opacity:0;':''}">+</span>
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

// ---- Drag & drop row reorder ----

let _schedDragSrcId = null;

function schedDragStart(event, trainerId) {
  _schedDragSrcId = trainerId;
  event.dataTransfer.effectAllowed = 'move';
  event.currentTarget.style.opacity = '0.4';
}

function schedDragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  // Highlight drop target row
  const row = event.currentTarget;
  row.style.borderTop = '2px solid var(--a)';
}

function schedDrop(event, targetId) {
  event.preventDefault();
  const row = event.currentTarget;
  row.style.borderTop = '';
  if (!_schedDragSrcId || _schedDragSrcId === targetId) return;

  // Reorder _schedTrainerOrder
  const trainers = schedGetOrderedTrainers();
  const ids = trainers.map(t => t.id);
  const srcIdx = ids.indexOf(_schedDragSrcId);
  const tgtIdx = ids.indexOf(targetId);
  if (srcIdx === -1 || tgtIdx === -1) return;
  ids.splice(srcIdx, 1);
  ids.splice(tgtIdx, 0, _schedDragSrcId);
  _schedTrainerOrder = ids;
  dbSaveTrainerOrder(ids);
  schedRenderContent();
}

function schedDragEnd(event) {
  event.currentTarget.style.opacity = '';
  event.currentTarget.style.borderTop = '';
  // Clean up all row borders
  document.querySelectorAll('.sched-grid tr').forEach(r => r.style.borderTop = '');
  _schedDragSrcId = null;
}

// ---- Multi-select & row management functions ----


function schedRemoveRow(trainerId, quart) {
  if (!window._schedExtraRows) window._schedExtraRows = {};
  const arr = window._schedExtraRows[trainerId] || [];
  window._schedExtraRows[trainerId] = arr.filter(q => q !== quart);
  schedRenderContent();
}

function schedOpenPatternForRow(trainerId, quart) {
  // Pre-fill pattern modal with trainer + quart
  const quartMap = { 'soir': 'BSP_SOIR', 'weekend': 'BSP_WEEKEND', 'jour': 'BSP_JOUR' };
  const patternKey = quartMap[quart] || null;
  schedOpenPatternModal(trainerId, patternKey, quart);
}

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
