// ==================== SCHEDULE: PATTERN GENERATOR ====================

function schedOpenRecurring(mode) {
  mode = mode || 'recurring';
  if (mode === 'pattern') { schedOpenPatternModal(); return; }
  const existing = document.getElementById('recurring-modal-overlay');
  if (existing) existing.remove();

  const trainerOpts = schedBuildTrainerOpts();

  const programOpts = `<option value="">— Aucun programme —</option>` +
    schedBuildProgramOpts();

  const currentYear = _schedYear;
  const nextYear    = currentYear + 1;

  const overlay = document.createElement('div');
  overlay.id = 'recurring-modal-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:2000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
  overlay.addEventListener('click', ev => { if (ev.target === overlay) overlay.remove(); });

  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:14px;width:480px;max-width:95vw;max-height:90vh;overflow-y:auto;display:flex;flex-direction:column;">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;border-bottom:1px solid var(--b);">
        <div>
          <h3 style="font-size:16px;font-weight:700;margin:0;">🔁 Horaire récurrent</h3>
          <div style="font-size:11px;color:var(--td);margin-top:3px;">Génère automatiquement les shifts pour toute une période</div>
        </div>
        <button onclick="document.getElementById('recurring-modal-overlay').remove()" style="background:none;border:none;color:var(--td);font-size:18px;cursor:pointer;">✕</button>
      </div>

      <div style="padding:18px 20px;display:flex;flex-direction:column;gap:14px;">

        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Formateur</label>
          <select id="rec_trainer" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            ${trainerOpts}
          </select>
        </div>

        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:8px;">Jours de la semaine</label>
          <div style="display:flex;gap:6px;">
            ${['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'].map((d,i) => `
              <label style="display:flex;flex-direction:column;align-items:center;gap:4px;cursor:pointer;flex:1;padding:6px 4px;border-radius:6px;border:1px solid var(--b);background:var(--bg);" id="rec_daylabel_${i}">
                <input type="checkbox" id="rec_day_${i}" value="${i}" ${i < 5 ? 'checked' : ''}
                  onchange="schedRecUpdatePreview()"
                  style="width:14px;height:14px;accent-color:var(--a);cursor:pointer;">
                <span style="font-size:10px;font-weight:600;">${d}</span>
              </label>`).join('')}
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Heure début</label>
            <input type="time" id="rec_start" value="08:00" onchange="schedRecUpdatePreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Heure fin</label>
            <input type="time" id="rec_end" value="16:00" onchange="schedRecUpdatePreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
        </div>

        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Programme <span style="opacity:0.5;">(optionnel)</span></label>
          <select id="rec_program" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            ${programOpts}
          </select>
        </div>

        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:8px;">Période</label>
          <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
            <button onclick="schedRecSetPeriod(${currentYear})" class="btn" id="rec_period_cy" style="font-size:11px;">Année ${currentYear}</button>
            <button onclick="schedRecSetPeriod(${nextYear})" class="btn" id="rec_period_ny" style="font-size:11px;">Année ${nextYear}</button>
            <button onclick="schedRecSetPeriod('custom')" class="btn" id="rec_period_custom" style="font-size:11px;">Dates custom</button>
          </div>
          <div id="rec_custom_dates" style="display:none;grid-template-columns:1fr 1fr;gap:10px;">
            <div>
              <label style="font-size:10px;color:var(--td);display:block;margin-bottom:3px;">Date début</label>
              <input type="date" id="rec_from" onchange="schedRecUpdatePreview()" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:12px;outline:none;"/>
            </div>
            <div>
              <label style="font-size:10px;color:var(--td);display:block;margin-bottom:3px;">Date fin</label>
              <input type="date" id="rec_to" onchange="schedRecUpdatePreview()" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:12px;outline:none;"/>
            </div>
          </div>
          <input type="hidden" id="rec_period_val" value="${currentYear}"/>
        </div>

        <div style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:rgba(255,107,53,0.06);border-radius:8px;border:1px solid rgba(255,107,53,0.2);">
          <input type="checkbox" id="rec_replace" style="width:15px;height:15px;accent-color:var(--a);cursor:pointer;">
          <label for="rec_replace" style="font-size:12px;cursor:pointer;color:var(--t);">Remplacer les shifts existants sur cette période</label>
        </div>

        <div id="rec_preview" style="font-size:12px;color:var(--td);text-align:center;padding:8px;background:var(--bg);border-radius:6px;"></div>
      </div>

      <div style="padding:14px 20px;border-top:1px solid var(--b);display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn" onclick="document.getElementById('recurring-modal-overlay').remove()">Annuler</button>
        <button class="btn primary" id="rec_save_btn" onclick="schedSaveRecurring()">Créer l'horaire</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);
  schedRecSetPeriod(currentYear);
}

function schedRecSetPeriod(val) {
  ['cy','ny','custom'].forEach(k => {
    const btn = document.getElementById('rec_period_' + k);
    if (btn) { btn.style.background = ''; btn.style.color = ''; }
  });
  const customDiv = document.getElementById('rec_custom_dates');
  const input = document.getElementById('rec_period_val');
  if (!input) return;

  if (val === 'custom') {
    input.value = 'custom';
    if (customDiv) customDiv.style.display = 'grid';
    const btn = document.getElementById('rec_period_custom');
    if (btn) { btn.style.background = 'var(--a)'; btn.style.color = '#fff'; }
  } else {
    input.value = String(val);
    if (customDiv) customDiv.style.display = 'none';
    const yr = parseInt(val) === _schedYear ? 'cy' : 'ny';
    const btn = document.getElementById('rec_period_' + yr);
    if (btn) { btn.style.background = 'var(--a)'; btn.style.color = '#fff'; }
  }
  schedRecUpdatePreview();
}

function schedRecGetDates() {
  const periodVal = document.getElementById('rec_period_val')?.value;
  let from, to;
  if (periodVal === 'custom') {
    from = document.getElementById('rec_from')?.value;
    to   = document.getElementById('rec_to')?.value;
    if (!from || !to) return [];
  } else {
    const yr = parseInt(periodVal);
    from = yr + '-01-01';
    to   = yr + '-12-31';
  }

  const selectedDays = [];
  for (let i = 0; i < 7; i++) {
    if (document.getElementById('rec_day_' + i)?.checked) selectedDays.push(i);
  }
  if (!selectedDays.length) return [];

  // Map our index (0=Lun…6=Dim) to JS getDay() (0=Sun,1=Mon…6=Sat)
  const jsDay = [1, 2, 3, 4, 5, 6, 0];
  const selectedJsDays = selectedDays.map(i => jsDay[i]);

  const dates = [];
  const end = new Date(to + 'T00:00:00');
  for (let d = new Date(from + 'T00:00:00'); d <= end; d.setDate(d.getDate() + 1)) {
    if (selectedJsDays.includes(d.getDay())) {
      dates.push(d.toISOString().slice(0, 10));
    }
  }
  return dates;
}

function schedRecUpdatePreview() {
  const preview = document.getElementById('rec_preview');
  if (!preview) return;
  const dates = schedRecGetDates();
  if (!dates.length) {
    preview.textContent = 'Sélectionne au moins un jour et une période.';
    preview.style.color = 'var(--td)';
  } else {
    preview.innerHTML = `<span style="color:var(--a);font-weight:700;">${dates.length} shifts</span> du <strong>${dates[0]}</strong> au <strong>${dates[dates.length-1]}</strong>`;
  }
}

async function schedSaveRecurring() {
  const instructor_id = document.getElementById('rec_trainer')?.value;
  const start_time    = document.getElementById('rec_start')?.value || '08:00';
  const end_time      = document.getElementById('rec_end')?.value   || '16:00';
  const program       = document.getElementById('rec_program')?.value || 'COORDINATION';
  const replace       = document.getElementById('rec_replace')?.checked;
  const dates         = schedRecGetDates();

  if (!instructor_id) { alert('Veuillez sélectionner un formateur.'); return; }
  if (!dates.length)  { alert('Aucune date générée. Vérifiez les jours et la période.'); return; }

  const saveBtn = document.getElementById('rec_save_btn');
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = `Création de ${dates.length} shifts...`; }

  try {
    if (replace) {
      const { error: delErr } = await db.from('schedule_entries')
        .delete()
        .eq('instructor_id', instructor_id)
        .gte('date', dates[0])
        .lte('date', dates[dates.length - 1]);
      if (delErr) throw delErr;
    }

    const entries = dates.map(date => ({
      instructor_id,
      date,
      shift_type: 'jour',
      program:    program || 'COORDINATION',
      start_time,
      end_time,
      status: 'confirmed',
      notes:  'Horaire récurrent'
    }));

    const BATCH = 50;
    let inserted = 0;
    const errors = [];
    for (let i = 0; i < entries.length; i += BATCH) {
      const { error } = await db.from('schedule_entries').insert(entries.slice(i, i + BATCH));
      if (error) { errors.push(error); continue; }
      inserted += BATCH;
      if (saveBtn) saveBtn.textContent = `${Math.min(inserted, dates.length)}/${dates.length} créés...`;
    }

    document.getElementById('recurring-modal-overlay')?.remove();
    await schedReloadEntries();

    const trainerName = schedGetTrainers().find(t => t.id === instructor_id)?.name || instructor_id;
    if (errors.length) {
      schedFlash(`${inserted}/${dates.length} shifts créés — ${errors.length} erreur(s)`, true);
    } else {
      schedFlash(`✓ ${dates.length} shifts créés pour ${trainerName}`);
    }
  } catch(err) {
    console.error('schedSaveRecurring error:', err);
    alert('Erreur: ' + (err.message || err));
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = "Créer l'horaire"; }
  }
}

// ==================== PATTERN COHORTE ====================

function schedOpenPatternModal(preTrainerId, prePatternKey, preQuart) {
  const existing = document.getElementById('pattern-modal-overlay');
  if (existing) existing.remove();

  const trainerOpts = schedBuildTrainerOpts();

  const patternOpts = Object.entries(SCHED_COHORT_PATTERNS).map(([k,p]) =>
    `<option value="${esc(k)}">${esc(p.label)}</option>`
  ).join('');

  const programOpts = schedBuildProgramOpts();

  const locationOpts = schedBuildLocationOpts();

  const overlay = document.createElement('div');
  overlay.id = 'pattern-modal-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:2000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
  overlay.addEventListener('click', ev => { if (ev.target === overlay) overlay.remove(); });

  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:14px;width:520px;max-width:95vw;max-height:90vh;overflow-y:auto;display:flex;flex-direction:column;">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;border-bottom:1px solid var(--b);">
        <div>
          <h3 style="font-size:16px;font-weight:700;margin:0;">📋 Générer par pattern de cohorte</h3>
          <div style="font-size:11px;color:var(--td);margin-top:3px;">Crée plusieurs cohortes consécutives en sautant les fériés automatiquement</div>
        </div>
        <button onclick="document.getElementById('pattern-modal-overlay').remove()" style="background:none;border:none;color:var(--td);font-size:18px;cursor:pointer;">✕</button>
      </div>

      <div style="padding:18px 20px;display:flex;flex-direction:column;gap:14px;">

        <!-- Formateur -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Formateur</label>
          <select id="pat_trainer" onchange="schedPatPreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            ${trainerOpts}
          </select>
        </div>

        <!-- Pattern -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Pattern</label>
          <select id="pat_pattern" onchange="schedPatOnPatternChange()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            ${patternOpts}
          </select>
        </div>


        <!-- Programme -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Programme</label>
          <select id="pat_program" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            ${programOpts}
          </select>
        </div>

                <!-- Salle / Lieu -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Salle / Lieu</label>
          <select id="pat_location" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
            <option value="">— Aucune salle —</option>
            ${locationOpts}
          </select>
        </div>

        <!-- Alternating config (hidden by default) -->
        <div id="pat_alternating_section" style="display:none;">
          <div style="background:var(--bg);border-radius:8px;padding:12px;margin-bottom:8px;">
            <div style="font-size:11px;color:var(--a);font-weight:700;margin-bottom:10px;">Groupe A (ex: Jeu+Ven)</div>
            <div style="display:flex;gap:8px;margin-bottom:8px;">
              ${['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'].map((d,i) =>
                `<label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;">
                  <input type="checkbox" value="${i}" name="pat_days_a" style="accent-color:var(--a);">
                  <span style="font-size:10px;">${d}</span>
                </label>`
              ).join('')}
            </div>
            <div style="font-size:11px;color:var(--a);font-weight:700;margin-bottom:10px;margin-top:10px;">Groupe B (ex: Sam+Dim)</div>
            <div style="display:flex;gap:8px;">
              ${['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'].map((d,i) =>
                `<label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;">
                  <input type="checkbox" value="${i}" name="pat_days_b" style="accent-color:var(--a);">
                  <span style="font-size:10px;">${d}</span>
                </label>`
              ).join('')}
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px;">
            <div>
              <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Fréquence</label>
              <select id="pat_alt_freq" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
                <option value="weekly">Chaque semaine</option>
                <option value="biweekly">1 semaine sur 2</option>
              </select>
            </div>
            <div>
              <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Nb de cohortes</label>
              <input id="pat_alt_count" type="number" value="26" min="1" max="100" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;box-sizing:border-box;">
            </div>
          </div>
        </div>

        <div id="pat_normal_section">
        <!-- Heures (modifiables) -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Heure début</label>
            <input type="time" id="pat_start" value="18:00" onchange="schedPatPreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Heure fin</label>
            <input type="time" id="pat_end" value="22:00" onchange="schedPatPreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
        </div>

        <!-- Première cohorte -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Date de début (1ère cohorte)</label>
            <input type="date" id="pat_startdate" onchange="schedPatPreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
          <div>
            <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Code 1ère cohorte</label>
            <input type="text" id="pat_firstcode" placeholder="ex: JS34" onchange="schedPatPreview()" style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"/>
          </div>
        </div>

        <!-- Nombre de cohortes -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Nombre de cohortes à générer</label>
          <div style="display:flex;align-items:center;gap:10px;">
            <input type="range" id="pat_count" min="1" max="20" value="5" oninput="document.getElementById('pat_count_lbl').textContent=this.value; schedPatPreview()" style="flex:1;accent-color:var(--a);">
            <span id="pat_count_lbl" style="font-size:14px;font-weight:700;color:var(--a);min-width:24px;">5</span>
          </div>
        </div>

        <!-- Gap entre cohortes -->
        <div>
          <label style="font-family:'Space Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:5px;">Pause entre cohortes <span style="opacity:0.5;">(jours)</span></label>
          <div style="display:flex;align-items:center;gap:10px;">
            <input type="range" id="pat_gap" min="0" max="42" value="4" oninput="document.getElementById('pat_gap_lbl').textContent=this.value; schedPatPreview()" style="flex:1;accent-color:var(--a);">
            <span id="pat_gap_lbl" style="font-size:14px;font-weight:700;color:var(--a);min-width:24px;">4</span>
          </div>
        </div>

        </div><!-- end pat_normal_section -->

        <!-- Aperçu -->
        <div id="pat_preview" style="background:var(--bg);border-radius:8px;border:1px solid var(--b);padding:12px;font-size:11px;max-height:200px;overflow-y:auto;"></div>

      </div>

      <div style="padding:14px 20px;border-top:1px solid var(--b);display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn" onclick="document.getElementById('pattern-modal-overlay').remove()">Annuler</button>
        <button class="btn primary" id="pat_save_btn" onclick="schedSavePattern()">Générer les cohortes</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);
  schedPatOnPatternChange();
  // Apply pre-fills if provided
  if (preTrainerId) {
    const ti = document.getElementById('pat_trainer');
    if (ti) ti.value = preTrainerId;
  }
  if (prePatternKey) {
    const pi = document.getElementById('pat_pattern');
    if (pi) { pi.value = prePatternKey; schedPatOnPatternChange(); }
  }
  if (preQuart) {
    const timeMap = { soir: {s:'18:00',e:'22:00'}, weekend: {s:'09:00',e:'17:00'}, jour: {s:'09:00',e:'17:00'} };
    const t = timeMap[preQuart];
    if (t) {
      const hs = document.getElementById('pat_start');
      const he = document.getElementById('pat_end');
      if (hs) hs.value = t.s;
      if (he) he.value = t.e;
    }
  }
  if (preQuart) {
    const progMap = { soir:'BSP', weekend:'BSP', jour:'BSP' };
    const pp = document.getElementById('pat_program');
    if (pp && progMap[preQuart]) pp.value = progMap[preQuart];
  }
  schedPatPreview();
}

function schedPatOnPatternChange() {
  const patKey = document.getElementById('pat_pattern')?.value;
  const altSection = document.getElementById('pat_alternating_section');
  const normalSection = document.getElementById('pat_normal_section');
  if (altSection && normalSection) {
    if (patKey === 'ALTERNATING') {
      altSection.style.display = 'block';
      normalSection.style.display = 'none';
    } else {
      altSection.style.display = 'none';
      normalSection.style.display = 'block';
    }
  }

  const key = document.getElementById('pat_pattern')?.value;
  const p = SCHED_COHORT_PATTERNS[key];
  if (!p) return;
  const startEl = document.getElementById('pat_start');
  const endEl   = document.getElementById('pat_end');
  const gapEl   = document.getElementById('pat_gap');
  const gapLbl  = document.getElementById('pat_gap_lbl');
  if (startEl) startEl.value = p.start_time;
  if (endEl)   endEl.value   = p.end_time;
  if (gapEl)   { gapEl.value = p.gap_days; }
  if (gapLbl)  gapLbl.textContent = p.gap_days;
  schedPatPreview();
}

function schedPatBuildAllCohorts() {
  const patKey    = document.getElementById('pat_pattern')?.value;
  const startDate = document.getElementById('pat_startdate')?.value;
  const firstCode = document.getElementById('pat_firstcode')?.value?.trim() || '';
  const count     = parseInt(document.getElementById('pat_count')?.value || '5');
  const gap       = parseInt(document.getElementById('pat_gap')?.value   || '4');
  const startTime = document.getElementById('pat_start')?.value || '18:00';
  const endTime   = document.getElementById('pat_end')?.value   || '22:00';
  const program   = document.getElementById('pat_program')?.value || null;
  const location_id = document.getElementById('pat_location')?.value || null;

  if (!patKey || !startDate) return [];
  const p = SCHED_COHORT_PATTERNS[patKey];
  if (!p) return [];

  // Parse first cohort number from code (e.g. "JS34" → prefix="JS", num=34)
  const match = firstCode.match(/^([A-Za-z]*)(\d+)$/);
  const prefix = match ? match[1] : (p.prefix || '');
  let   num    = match ? parseInt(match[2]) : 1;

  const cohorts = [];
  let cursor = startDate;

  for (let c = 0; c < count; c++) {
    const year = parseInt(cursor.slice(0,4));
    const dates = schedGenCohortDates(patKey, cursor, year);
    if (!dates.length) break;

    cohorts.push({
      code:      prefix + num,
      dates,
      startTime,
      endTime,
      program:   program || p.program,
      shiftType: p.shift_type,
      locationId: location_id,
    });
    num++;

    // Next cohort starts gap days after last date of this cohort
    const last = new Date(dates[dates.length-1] + 'T00:00:00');
    last.setDate(last.getDate() + gap + 1);
    cursor = last.toISOString().slice(0,10);
  }
  return cohorts;
}

function schedPatPreview() {
  const preview = document.getElementById('pat_preview');
  if (!preview) return;

  const patKey2 = document.getElementById('pat_pattern')?.value;
  const cohorts = patKey2 === 'ALTERNATING' ? schedPatBuildAlternating() : schedPatBuildAllCohorts();
  if (!cohorts.length) {
    preview.innerHTML = '<span style="color:var(--td);">Remplis les champs pour voir l\'aperçu.</span>';
    return;
  }

  const holidays = schedGetHolidaysQC(parseInt(cohorts[0].dates[0].slice(0,4)));
  schedGetHolidaysQC(parseInt(cohorts[0].dates[0].slice(0,4)) + 1).forEach(h => holidays.add(h));

  let html = `<div style="color:var(--a);font-weight:700;margin-bottom:8px;">${cohorts.length} cohortes · ${cohorts.reduce((s,c)=>s+c.dates.length,0)} shifts total</div>`;
  cohorts.forEach(c => {
    const skipped = []; // holidays that were skipped — we can show them
    html += `<div style="margin-bottom:6px;padding:6px 8px;background:rgba(255,255,255,0.04);border-radius:5px;">
      <span style="font-family:'Space Mono',monospace;font-size:10px;color:var(--a);font-weight:700;">${esc(c.code)}</span>
      <span style="color:var(--td);font-size:10px;"> · ${c.dates.length} jours · ${c.dates[0]} → ${c.dates[c.dates.length-1]}</span>
      <div style="font-size:9px;color:var(--td);margin-top:2px;opacity:0.7;">${c.startTime}–${c.endTime} · ${c.dates.join(' · ')}</div>
    </div>`;
  });
  preview.innerHTML = html;
}

function schedPatBuildAlternating() {
  const instructorId = document.getElementById('pat_trainer')?.value;
  const startDate    = document.getElementById('pat_startdate')?.value;
  const firstCode    = document.getElementById('pat_firstcode')?.value?.trim() || 'MC1';
  const startTime    = document.getElementById('pat_start')?.value || '09:00';
  const endTime      = document.getElementById('pat_end')?.value   || '17:00';
  const program      = document.getElementById('pat_program')?.value || 'RCR';
  const location_id  = document.getElementById('pat_location')?.value || null;
  const freq         = document.getElementById('pat_alt_freq')?.value || 'weekly';
  const totalCount   = parseInt(document.getElementById('pat_alt_count')?.value || '26');

  const daysA = [...document.querySelectorAll('input[name="pat_days_a"]:checked')].map(el => parseInt(el.value));
  const daysB = [...document.querySelectorAll('input[name="pat_days_b"]:checked')].map(el => parseInt(el.value));

  if (!startDate || daysA.length === 0 || daysB.length === 0) return [];

  const holidays = schedGetHolidaysQC(parseInt(startDate.slice(0,4)));
  schedGetHolidaysQC(parseInt(startDate.slice(0,4))+1).forEach(h => holidays.add(h));

  // Parse starting code number
  const match = firstCode.match(/^([A-Za-z]*)(\d+)$/);
  const prefix = match ? match[1] : 'MC';
  let num = match ? parseInt(match[2]) : 1;

  // Find Monday of the start week
  let d = new Date(startDate + 'T00:00:00');
  while (d.getDay() !== 1) d.setDate(d.getDate() - 1); // go back to Monday
  if (d > new Date(startDate + 'T00:00:00')) d.setDate(d.getDate() - 7);

  const anchorMon = new Date(d);
  const cohorts = [];
  let weekOffset = 0;

  while (cohorts.length < totalCount) {
    const isOnWeek = freq === 'weekly' || (weekOffset % 2 === 0);

    if (isOnWeek) {
      // Group A: collect days from this week
      const gA = [];
      daysA.forEach(dow => {
        const dd = new Date(d);
        const diff = (dow - 1 + 7) % 7; // offset from Monday
        dd.setDate(d.getDate() + diff);
        const iso = dd.toISOString().slice(0,10);
        if (!holidays.has(iso)) gA.push(iso);
      });
      gA.sort();

      // Group B: collect days from this week (Sam/Dim may be in same or next week)
      const gB = [];
      daysB.forEach(dow => {
        const dd = new Date(d);
        // Sunday(0) is end of week = +6 from Monday
        const diff = dow === 0 ? 6 : (dow - 1);
        dd.setDate(d.getDate() + diff);
        // If Sam/Dim, they're at end of week (+5,+6)
        if (dow === 6) dd.setDate(d.getDate() + 5);
        if (dow === 0) dd.setDate(d.getDate() + 6);
        const iso = dd.toISOString().slice(0,10);
        if (!holidays.has(iso)) gB.push(iso);
      });
      gB.sort();

      if (gA.length > 0 && cohorts.length < totalCount) {
        cohorts.push({ code: prefix+num, dates: gA, startTime, endTime, program, shiftType: freq==='weekly'?'jour':'jour', locationId: location_id });
        num++;
      }
      if (gB.length > 0 && cohorts.length < totalCount) {
        cohorts.push({ code: prefix+num, dates: gB, startTime, endTime, program, shiftType: 'weekend', locationId: location_id });
        num++;
      }
    }

    d.setDate(d.getDate() + 7);
    weekOffset++;
    if (weekOffset > 200) break; // safety
  }
  return cohorts;
}

async function schedSavePattern() {
  const instructor_id = document.getElementById('pat_trainer')?.value;
  if (!instructor_id) { alert('Sélectionne un formateur.'); return; }

  const patKey = document.getElementById('pat_pattern')?.value;
  const cohorts = patKey === 'ALTERNATING' ? schedPatBuildAlternating() : schedPatBuildAllCohorts();
  if (!cohorts.length) { alert('Aucune cohorte générée. Vérifie les paramètres.'); return; }

  const saveBtn = document.getElementById('pat_save_btn');
  const totalShifts = cohorts.reduce((s,c) => s + c.dates.length, 0);
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = `Création de ${totalShifts} shifts...`; }

  try {
    const allEntries = [];
    cohorts.forEach(c => {
      c.dates.forEach(date => {
        allEntries.push({
          instructor_id,
          date,
          shift_type:     c.shiftType,
          program:        c.program,
          location_id:    c.locationId || null,
          excel_cell_code: c.code,
          start_time:     c.startTime,
          end_time:       c.endTime,
          status:         'scheduled',
          notes:          `Cohorte ${c.code}`,
        });
      });
    });

    const BATCH = 50;
    let inserted = 0;
    for (let i = 0; i < allEntries.length; i += BATCH) {
      const { error } = await db.from('schedule_entries').insert(allEntries.slice(i, i + BATCH));
      if (error) throw error;
      inserted += BATCH;
      if (saveBtn) saveBtn.textContent = `${Math.min(inserted, totalShifts)}/${totalShifts} créés...`;
    }

    document.getElementById('pattern-modal-overlay')?.remove();
    await schedReloadEntries();

    const trainerName = schedGetTrainers().find(t => t.id === instructor_id)?.name || instructor_id;
    schedFlash(`✓ ${cohorts.length} cohortes créées pour ${trainerName} (${totalShifts} shifts)`);
  } catch(err) {
    console.error('schedSavePattern error:', err);
    alert('Erreur: ' + (err.message || err));
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Générer les cohortes'; }
  }
}
