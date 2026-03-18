// ==================== SCHEDULE: SHIFT MODAL ====================

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
    </div>
    <div style="margin-top:6px;padding-top:8px;border-top:1px solid var(--b);">
      <button class="btn" style="font-size:11px;padding:5px 10px;width:100%;background:var(--s2,#1e293b);" onclick="schedManageSeries('${esc(entry.instructor_id)}')">📋 Gérer toutes les séries</button>
    </div>
    `;

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

  const isEdit   = !!_schedModalEntry;
  const e        = _schedModalEntry || {};
  const pf       = _schedModalPrefill;

  const trainerOpts = schedBuildTrainerOpts(e.instructor_id || pf.instructor_id);

  const programOpts = schedBuildProgramOpts(e.program || pf.program);

  const locationOpts = schedBuildLocationOpts(e.location_id);

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
