// ==================== SCHEDULE: AUTO RULES ====================

// ==================== HORAIRE RÉCURRENT + PATTERN COHORTE ====================

// ============================================================
// AUTO RULES — recurring schedules per trainer
// ============================================================
// Rules stored in localStorage as JSON array:
// [{ instructorId, days:[0-6], frequency:'weekly'|'biweekly', anchorDate,
//    program, start_time, end_time, shift_type, code_prefix, location_id }]

function schedGetAutoRules() {
  try { return JSON.parse(localStorage.getItem('xg_auto_rules') || '[]'); } catch { return []; }
}
function schedSaveAutoRules(rules) {
  localStorage.setItem('xg_auto_rules', JSON.stringify(rules));
}

function schedOpenAutoRules() {
  const existing = document.getElementById('auto-rules-overlay');
  if (existing) existing.remove();

  const trainers = schedGetOrderedTrainers();
  const trainerOpts = schedBuildTrainerOpts();

  const programOpts = schedBuildProgramOpts();

  const locationOpts = schedBuildLocationOpts();

  const rules = schedGetAutoRules();
  const rulesHTML = rules.length === 0
    ? '<div style="color:var(--td);font-size:12px;text-align:center;padding:12px;">Aucune règle définie.</div>'
    : rules.map((r, i) => {
        const trainer = trainers.find(t => t.id === r.instructorId);
        const DAYNAMES = ['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
        const daysStr = r.days.map(d => DAYNAMES[d]).join('+');
        const freqStr = r.frequency === 'biweekly' ? '1 sem/2' : 'chaque sem';
        return `<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--bg);border-radius:6px;margin-bottom:6px;">
          <div style="flex:1;font-size:12px;">
            <strong>${esc(trainer ? trainer.name : r.instructorId)}</strong>
            <span style="color:var(--td);margin-left:6px;">${daysStr} · ${freqStr} · ${r.program} · ${r.start_time}–${r.end_time}</span>
          </div>
          <button onclick="schedDeleteAutoRule(${i})" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:16px;padding:0 4px;">🗑</button>
        </div>`;
      }).join('');

  const overlay = document.createElement('div');
  overlay.id = 'auto-rules-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:3000;display:flex;align-items:center;justify-content:center;';
  overlay.innerHTML = `
    <div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:24px;width:560px;max-height:85vh;overflow-y:auto;font-family:'DM Sans',sans-serif;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div>
          <div style="font-size:15px;font-weight:700;">⚙️ Règles automatiques</div>
          <div style="font-size:11px;color:var(--td);">Définir des horaires récurrents par formateur</div>
        </div>
        <button onclick="document.getElementById('auto-rules-overlay').remove()" style="background:none;border:none;color:var(--td);font-size:20px;cursor:pointer;">✕</button>
      </div>

      <!-- Existing rules -->
      <div id="auto-rules-list" style="margin-bottom:16px;">${rulesHTML}</div>

      <!-- Add new rule form -->
      <div style="border:1px solid var(--b);border-radius:8px;padding:16px;">
        <div style="font-size:12px;font-weight:700;margin-bottom:12px;color:var(--a);">+ Nouvelle règle</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Formateur</label>
            <select id="ar_trainer" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">${trainerOpts}</select>
          </div>
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Programme</label>
            <select id="ar_program" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">${programOpts}</select>
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:6px;">Jours de la semaine</label>
          <div style="display:flex;gap:6px;">
            ${['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'].map((d,i) =>
              `<label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;">
                <input type="checkbox" value="${i}" name="ar_days" style="accent-color:var(--a);">
                <span style="font-size:10px;">${d}</span>
              </label>`
            ).join('')}
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Fréquence</label>
            <select id="ar_freq" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
              <option value="weekly">Chaque semaine</option>
              <option value="biweekly">1 semaine sur 2</option>
            </select>
          </div>
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Heure début</label>
            <input id="ar_start" type="time" value="09:00" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
          </div>
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Heure fin</label>
            <input id="ar_end" type="time" value="17:00" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;">
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:12px;">
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Salle</label>
            <select id="ar_location" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;"><option value="">— Aucune —</option>${locationOpts}</select>
          </div>
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Code préfixe</label>
            <input id="ar_prefix" type="text" placeholder="ex: WL" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;box-sizing:border-box;">
          </div>
          <div>
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Date ancrage (si 1/2)</label>
            <input id="ar_anchor" type="date" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;box-sizing:border-box;">
          </div>
        </div>

        <button onclick="schedAddAutoRule()" class="btn primary" style="width:100%;padding:8px;font-size:13px;">+ Ajouter cette règle</button>
      </div>

      <!-- Generate section -->
      <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--b);">
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="flex:1;">
            <label style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--td);display:block;margin-bottom:4px;">Générer jusqu'au</label>
            <input id="ar_until" type="date" value="2026-12-31" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--b);background:var(--bg);color:var(--t);font-size:13px;outline:none;box-sizing:border-box;">
          </div>
          <button onclick="schedGenerateAutoRules()" class="btn primary" style="padding:10px 20px;font-size:13px;margin-top:16px;">⚡ Générer tous les shifts</button>
        </div>
        <div style="font-size:11px;color:var(--td);margin-top:6px;">Saute automatiquement les fériés et les dates déjà planifiées.</div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
}

function schedAddAutoRule() {
  const instructorId = document.getElementById('ar_trainer')?.value;
  const program      = document.getElementById('ar_program')?.value;
  const frequency    = document.getElementById('ar_freq')?.value || 'weekly';
  const start_time   = document.getElementById('ar_start')?.value || '09:00';
  const end_time     = document.getElementById('ar_end')?.value || '17:00';
  const location_id  = document.getElementById('ar_location')?.value || null;
  const code_prefix  = document.getElementById('ar_prefix')?.value?.trim() || '';
  const anchorDate   = document.getElementById('ar_anchor')?.value || null;

  const days = [...document.querySelectorAll('input[name="ar_days"]:checked')].map(el => parseInt(el.value));
  if (!instructorId || days.length === 0) {
    alert('Sélectionne un formateur et au moins un jour.');
    return;
  }

  const rules = schedGetAutoRules();
  rules.push({ instructorId, days, frequency, anchorDate, program, start_time, end_time, location_id, code_prefix });
  schedSaveAutoRules(rules);
  schedOpenAutoRules(); // refresh
}

function schedDeleteAutoRule(index) {
  const rules = schedGetAutoRules();
  rules.splice(index, 1);
  schedSaveAutoRules(rules);
  schedOpenAutoRules();
}

async function schedGenerateAutoRules() {
  const untilDate = document.getElementById('ar_until')?.value;
  if (!untilDate) { alert('Choisis une date de fin.'); return; }

  const rules = schedGetAutoRules();
  if (!rules.length) { alert('Aucune règle définie.'); return; }

  const startYear = new Date().getFullYear();
  const holidays = schedGetHolidaysQC(startYear);
  schedGetHolidaysQC(startYear + 1).forEach(h => holidays.add(h));

  const todayStr = new Date().toISOString().slice(0,10);

  // Fetch all existing entries to avoid duplicates
  const {data: existing} = await db.from('schedule_entries')
    .select('instructor_id, date')
    .gte('date', todayStr)
    .lte('date', untilDate);

  const existingSet = new Set((existing||[]).map(e => e.instructor_id + '|' + e.date));

  const toInsert = [];
  let weekNum = {};

  rules.forEach(rule => {
    const anchor = rule.anchorDate || todayStr;
    // For biweekly: determine which weeks are "on" based on anchor date's week
    const anchorD = new Date(anchor + 'T00:00:00');
    const anchorMon = new Date(anchorD);
    anchorMon.setDate(anchorD.getDate() - ((anchorD.getDay() + 6) % 7)); // Monday of anchor week

    let d = new Date(todayStr + 'T00:00:00');
    // Align to next valid day
    const until = new Date(untilDate + 'T00:00:00');

    while (d <= until) {
      const iso = d.toISOString().slice(0,10);
      const dow = d.getDay();

      if (rule.days.includes(dow) && !holidays.has(iso)) {
        // Check biweekly: is this week an "on" week?
        let include = true;
        if (rule.frequency === 'biweekly') {
          const thisMon = new Date(d);
          thisMon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
          const weekDiff = Math.round((thisMon - anchorMon) / (7 * 86400000));
          include = weekDiff % 2 === 0;
        }

        if (include && !existingSet.has(rule.instructorId + '|' + iso)) {
          toInsert.push({
            instructor_id: rule.instructorId,
            date:          iso,
            program:       rule.program || null,
            start_time:    rule.start_time,
            end_time:      rule.end_time,
            location_id:   rule.location_id || null,
            shift_type:    'jour',
            status:        'scheduled',
            excel_cell_code: rule.code_prefix || null,
          });
          existingSet.add(rule.instructorId + '|' + iso);
        }
      }
      d.setDate(d.getDate() + 1);
    }
  });

  if (!toInsert.length) {
    showFlash('Aucun nouveau shift à créer (déjà planifiés ou aucune date valide).');
    document.getElementById('auto-rules-overlay')?.remove();
    return;
  }

  // Insert in batches
  const BATCH = 50;
  let inserted = 0;
  for (let i = 0; i < toInsert.length; i += BATCH) {
    const {error} = await db.from('schedule_entries').insert(toInsert.slice(i, i+BATCH));
    if (!error) inserted += Math.min(BATCH, toInsert.length - i);
  }

  showFlash(`✅ ${inserted} shift${inserted>1?'s':''} créé${inserted>1?'s':''} selon les règles auto`);
  document.getElementById('auto-rules-overlay')?.remove();
  await schedReloadEntries();
  schedRenderContent();
}
