// ==================== SCHEDULE: SERIES MANAGER ====================

// ---- Shift Detail Popup ----

async function schedManageSeries(instructorId) {
  schedClosePopup();
  const trainer = data.find(p => p.id === instructorId);
  const trainerName = trainer ? trainer.name : instructorId;

  // Fetch ALL entries for this trainer from Supabase (all months/years)
  const { data: allEntries, error } = await db
    .from('schedule_entries')
    .select('id, date, excel_cell_code, program, shift_type')
    .eq('instructor_id', instructorId)
    .not('excel_cell_code', 'is', null)
    .order('date', { ascending: true });

  const entries = allEntries || [];
  const seriesMap = {};
  entries.forEach(e => {
    const k = e.excel_cell_code;
    if (!k) return;
    if (!seriesMap[k]) seriesMap[k] = { code: k, count: 0, min: e.date, max: e.date, program: e.program };
    seriesMap[k].count++;
    if (e.date < seriesMap[k].min) seriesMap[k].min = e.date;
    if (e.date > seriesMap[k].max) seriesMap[k].max = e.date;
  });
  const series = Object.values(seriesMap).sort((a,b) => a.min.localeCompare(b.min));

  const existing = document.getElementById('manage-series-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'manage-series-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:3000;display:flex;align-items:center;justify-content:center;';

  // Compute trainer initials using shared initials() from utils.js
  const trainerInitials = initials(trainerName);

  const rowsHTML = series.length === 0
    ? '<div style="color:var(--td);font-size:12px;text-align:center;padding:20px;">Aucune série trouvée pour ce formateur.</div>'
    : series.map(s => `
      <div style="display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--b);">
        <div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <input id="rename_${esc(s.code)}" type="text" value="${esc(s.code)}" style="flex:1;padding:5px 8px;border-radius:5px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;font-weight:700;outline:none;" />
            <span style="font-size:10px;color:var(--td);white-space:nowrap;">→ affiché: <strong style="color:var(--a);">${esc(s.code)}-${trainerInitials}</strong></span>
          </div>
          <div style="font-size:10px;color:var(--td);">${s.count} shifts · ${s.min} → ${s.max}</div>
        </div>
        <button onclick="schedApplySeriesRename('${esc(instructorId)}','${esc(s.code)}')" class="btn" style="font-size:11px;padding:5px 10px;white-space:nowrap;">✎ Appliquer</button>
        <button onclick="schedDeleteSeriesFromManager('${esc(instructorId)}','${esc(s.code)}')" class="btn danger" style="font-size:11px;padding:5px 10px;white-space:nowrap;">🗑</button>
      </div>
    `).join('');

  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:24px;width:480px;max-height:80vh;overflow-y:auto;font-family:'DM Sans',sans-serif;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div>
          <div style="font-size:15px;font-weight:700;">Séries de ${esc(trainerName)}</div>
          <div style="font-size:11px;color:var(--td);">Modifiez les codes ou supprimez des séries en lot</div>
        </div>
        <button onclick="document.getElementById('manage-series-overlay').remove()" style="background:none;border:none;color:var(--td);font-size:20px;cursor:pointer;line-height:1;">✕</button>
      </div>
      ${rowsHTML}
      <div style="margin-top:16px;text-align:right;">
        <button onclick="document.getElementById('manage-series-overlay').remove()" style="padding:8px 20px;border-radius:6px;border:1px solid var(--b);background:transparent;color:var(--t);cursor:pointer;font-size:13px;">Fermer</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
}

async function schedApplySeriesRename(instructorId, oldCode) {
  const newCode = document.getElementById('rename_' + oldCode)?.value?.trim();
  if (!newCode || newCode === oldCode) return;
  // Query Supabase directly so rename works across all months, not just the loaded cache
  const { data: toUpdate, error: fetchErr } = await db.from('schedule_entries')
    .select('id')
    .eq('instructor_id', instructorId)
    .eq('excel_cell_code', oldCode);
  if (fetchErr) { schedFlash('Erreur: ' + fetchErr.message); return; }
  let updated = 0;
  for (const e of (toUpdate || [])) {
    const { error } = await db.from('schedule_entries').update({ excel_cell_code: newCode }).eq('id', e.id);
    if (!error) updated++;
  }
  schedFlash(`${updated} shift${updated>1?'s':''} → ${newCode}`);
  await schedReloadEntries();
  schedRenderContent();
  document.getElementById('manage-series-overlay')?.remove();
  schedManageSeries(instructorId);
}

async function schedDeleteSeriesFromManager(instructorId, code) {
  const overlay2 = document.createElement('div');
  overlay2.id = 'del-confirm-overlay';
  overlay2.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:4000;display:flex;align-items:center;justify-content:center;';
  overlay2.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:10px;padding:24px;width:340px;font-family:'DM Sans',sans-serif;">
      <div style="font-size:14px;font-weight:700;margin-bottom:8px;">Supprimer la série <span style="color:var(--a);">${esc(code)}</span> ?</div>
      <div style="font-size:12px;color:var(--td);margin-bottom:16px;">Choisissez ce que vous voulez supprimer :</div>
      <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer;">
        <input type="radio" name="del2_mode" value="all" checked style="accent-color:var(--a);"> Toute la série
      </label>
      <label style="display:flex;align-items:center;gap:8px;margin-bottom:4px;cursor:pointer;">
        <input type="radio" name="del2_mode" value="from" style="accent-color:var(--a);" onchange="document.getElementById('del2_date_wrap').style.display='block'"> À partir d'une date
      </label>
      <div id="del2_date_wrap" style="display:none;margin-bottom:12px;padding-left:20px;">
        <input type="date" id="del2_from_date" style="padding:6px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;" />
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px;">
        <button onclick="document.getElementById('del-confirm-overlay').remove()" style="padding:8px 16px;border-radius:6px;border:1px solid var(--b);background:transparent;color:var(--t);cursor:pointer;font-size:13px;">Annuler</button>
        <button onclick="schedExecDeleteFromManager('${esc(instructorId)}','${esc(code)}')" style="padding:8px 16px;border-radius:6px;background:#ef4444;color:#fff;border:none;cursor:pointer;font-size:13px;font-weight:600;">Supprimer</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay2);
}

async function schedExecDeleteFromManager(instructorId, code) {
  const mode = document.querySelector('input[name="del2_mode"]:checked')?.value || 'all';
  const fromDate = document.getElementById('del2_from_date')?.value || null;
  document.getElementById('del-confirm-overlay')?.remove();

  // Query Supabase directly so delete works across all months, not just the loaded cache
  let query = db.from('schedule_entries')
    .select('id')
    .eq('instructor_id', instructorId)
    .eq('excel_cell_code', code);
  if (mode === 'from' && fromDate) query = query.gte('date', fromDate);
  const { data: toDelete, error: fetchErr } = await query;
  if (fetchErr) { schedFlash('Erreur: ' + fetchErr.message); return; }

  const ids = (toDelete || []).map(e => e.id);
  let deleted = 0;
  for (let i = 0; i < ids.length; i += 50) {
    const { error } = await db.from('schedule_entries').delete().in('id', ids.slice(i, i+50));
    if (!error) deleted += Math.min(50, ids.length - i);
  }
  schedFlash(`${deleted} shift${deleted>1?'s':''} supprimé${deleted>1?'s':''}`);
  await schedReloadEntries();
  schedRenderContent();
  document.getElementById('manage-series-overlay')?.remove();
  schedManageSeries(instructorId);
}

async function schedDeleteSeriesPrompt(entryId, code, entryDate) {
  const overlay = document.createElement('div');
  overlay.id = 'delete-series-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:3000;display:flex;align-items:center;justify-content:center;';
  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:24px;width:360px;font-family:'DM Sans',sans-serif;">
      <div style="font-size:14px;font-weight:700;margin-bottom:6px;">Supprimer la série <span style="color:var(--a);">${esc(code)}</span></div>
      <div style="font-size:12px;color:var(--td);margin-bottom:16px;">Choisissez ce que vous voulez supprimer.</div>

      <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:20px;">
        <label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:10px;border-radius:8px;border:1px solid var(--b);background:var(--bg);">
          <input type="radio" name="del_mode" value="all" checked style="accent-color:var(--a);width:16px;height:16px;">
          <div>
            <div style="font-size:13px;font-weight:600;">Toute la série</div>
            <div style="font-size:11px;color:var(--td);">Supprime tous les shifts avec le code ${esc(code)}</div>
          </div>
        </label>
        <label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:10px;border-radius:8px;border:1px solid var(--b);background:var(--bg);">
          <input type="radio" name="del_mode" value="from" style="accent-color:var(--a);width:16px;height:16px;" onchange="document.getElementById('del_from_date_wrap').style.display='block'">
          <div style="flex:1;">
            <div style="font-size:13px;font-weight:600;">À partir d'une date</div>
            <div style="font-size:11px;color:var(--td);">Supprime seulement les shifts à partir de la date choisie</div>
          </div>
        </label>
        <div id="del_from_date_wrap" style="display:none;padding:0 10px;">
          <input type="date" id="del_from_date" value="${esc(entryDate)}" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;box-sizing:border-box;" />
        </div>
      </div>

      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button onclick="document.getElementById('delete-series-overlay').remove()" style="padding:8px 16px;border-radius:6px;border:1px solid var(--b);background:transparent;color:var(--t);cursor:pointer;font-size:13px;">Annuler</button>
        <button onclick="schedDeleteSeries('${esc(entryId)}','${esc(code)}')" style="padding:8px 16px;border-radius:6px;background:#ef4444;color:#fff;border:none;cursor:pointer;font-size:13px;font-weight:600;">Supprimer</button>
      </div>
    </div>
  `;
  // Wire up radio to show/hide date input
  overlay.querySelectorAll && setTimeout(() => {
    const radios = document.querySelectorAll('input[name="del_mode"]');
    radios.forEach(r => r.addEventListener('change', () => {
      const wrap = document.getElementById('del_from_date_wrap');
      if (wrap) wrap.style.display = r.value === 'from' ? 'block' : 'none';
    }));
  }, 50);
  document.body.appendChild(overlay);
}

async function schedDeleteSeries(entryId, code) {
  const mode = document.querySelector('input[name="del_mode"]:checked')?.value || 'all';
  const fromDate = document.getElementById('del_from_date')?.value || null;

  const entry = _schedEntries.find(e => e.id === entryId);
  if (!entry) return;
  const instructorId = entry.instructor_id;

  document.getElementById('delete-series-overlay')?.remove();
  schedClosePopup();

  // Filter entries to delete
  let toDelete = _schedEntries.filter(e =>
    e.instructor_id === instructorId && e.excel_cell_code === code
  );
  if (mode === 'from' && fromDate) {
    toDelete = toDelete.filter(e => e.date >= fromDate);
  }

  if (!toDelete.length) {
    schedFlash('Aucun shift trouvé à supprimer.', true);
    return;
  }

  const ids = toDelete.map(e => e.id);
  let deleted = 0;
  const BATCH = 50;
  for (let i = 0; i < ids.length; i += BATCH) {
    const batch = ids.slice(i, i + BATCH);
    const { error } = await db.from('schedule_entries').delete().in('id', batch);
    if (!error) deleted += batch.length;
  }

  schedFlash(`${deleted} shift${deleted>1?'s':''} supprimé${deleted>1?'s':''}`, false);
  await schedReloadEntries();
  schedRenderContent();
}

async function schedRenameSeriesPrompt(entryId, currentCode) {
  // Show inline rename modal
  const overlay = document.createElement('div');
  overlay.id = 'rename-series-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:3000;display:flex;align-items:center;justify-content:center;';
  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:24px;width:340px;font-family:'DM Sans',sans-serif;">
      <div style="font-size:14px;font-weight:700;margin-bottom:6px;">Renommer la série</div>
      <div style="font-size:12px;color:var(--td);margin-bottom:16px;">Tous les shifts avec le code <strong>${esc(currentCode)}</strong> pour ce formateur seront renommés.</div>
      <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Nouveau code</label>
      <input id="rename_new_code" type="text" value="${esc(currentCode)}" placeholder="ex: JS35" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:14px;outline:none;box-sizing:border-box;margin-bottom:16px;" />
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button onclick="document.getElementById('rename-series-overlay').remove()" style="padding:8px 16px;border-radius:6px;border:1px solid var(--b);background:transparent;color:var(--t);cursor:pointer;font-size:13px;">Annuler</button>
        <button onclick="schedRenameSeries('${esc(entryId)}','${esc(currentCode)}')" class="btn primary" style="padding:8px 16px;font-size:13px;">Renommer</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  const inp = document.getElementById('rename_new_code');
  if (inp) { inp.focus(); inp.select(); }
}

async function schedRenameSeries(entryId, oldCode) {
  const newCode = document.getElementById('rename_new_code')?.value?.trim();
  if (!newCode || newCode === oldCode) {
    document.getElementById('rename-series-overlay')?.remove();
    return;
  }
  const entry = _schedEntries.find(e => e.id === entryId);
  if (!entry) return;
  const instructorId = entry.instructor_id;

  // Find all entries with same instructor + same code
  const toUpdate = _schedEntries.filter(e =>
    e.instructor_id === instructorId && e.excel_cell_code === oldCode
  );

  document.getElementById('rename-series-overlay')?.remove();
  schedClosePopup();

  let updated = 0;
  for (const e of toUpdate) {
    const { error } = await db.from('schedule_entries')
      .update({ excel_cell_code: newCode })
      .eq('id', e.id);
    if (!error) updated++;
  }

  schedFlash(`${updated} shift${updated>1?'s':''} renommé${updated>1?'s':''} → ${newCode}`);
  await schedReloadEntries();
  schedRenderContent();
}
