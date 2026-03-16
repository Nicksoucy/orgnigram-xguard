// ==================== WEEKLY REPORT MODAL ====================

// People who submit weekly reports: person_id → their team members to track
const REPORT_PEOPLE = {
  'L3': { label: 'Service à la clientèle', agents: ['L3','s2','s3'], agentNames: {'L3':'Hamza','s2':'Lilia','s3':'Sekou'} }
};

function openWeeklyReport(pid) {
  // Get monday/sunday of current week
  const now = new Date();
  const day = now.getDay();
  const mon = new Date(now); mon.setDate(now.getDate() - (day===0?6:day-1));
  const sun = new Date(mon); sun.setDate(mon.getDate()+6);
  const fmt = d => d.toISOString().split('T')[0];

  const cfg = REPORT_PEOPLE[pid] || { label: 'Rapport', agents: [pid], agentNames: {[pid]: data.find(p=>p.id===pid)?.name||pid} };
  const person = data.find(p=>p.id===pid) || VP;

  document.getElementById('rmo').style.display='flex';
  document.getElementById('rmo').innerHTML = `
  <div class="mo-box" style="max-width:640px;width:100%;max-height:90vh;overflow-y:auto;">
    <div class="mo-head">
      <span>📋 Rapport hebdomadaire — ${esc(person.name)}</span>
      <button class="mo-close" onclick="closeReportModal()">✕</button>
    </div>
    <div class="mo-body">
      <div style="display:flex;gap:12px;margin-bottom:16px;">
        <div style="flex:1;">
          <label class="mo-label">Semaine du</label>
          <input type="date" id="rp-week-start" class="mo-input" value="${fmt(mon)}"/>
        </div>
        <div style="flex:1;">
          <label class="mo-label">au</label>
          <input type="date" id="rp-week-end" class="mo-input" value="${fmt(sun)}"/>
        </div>
      </div>

      <div class="rp-section-title">📞 Volume d'appels <span style="font-size:10px;opacity:0.5;">(tiré de JustCall)</span></div>
      <table class="rp-table">
        <thead><tr><th>Agent</th><th>Entrants</th><th>Sortants</th></tr></thead>
        <tbody>
          ${cfg.agents.map(a=>`
          <tr>
            <td>${cfg.agentNames[a]||a}</td>
            <td><input type="number" min="0" class="rp-num" id="rp-in-${a}" placeholder="0"/></td>
            <td><input type="number" min="0" class="rp-num" id="rp-out-${a}" placeholder="0"/></td>
          </tr>`).join('')}
        </tbody>
      </table>
      <div style="display:flex;gap:12px;margin-top:8px;margin-bottom:16px;">
        <div style="flex:1;">
          <label class="mo-label">Taux de réponse (%)</label>
          <input type="number" min="0" max="100" id="rp-answer-rate" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="ex: 87"/>
        </div>
      </div>

      <div class="rp-section-title">🎓 Inscriptions conclues via SAC</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;">
        <div><label class="mo-label">BSP Gardiennage</label><input type="number" min="0" id="rp-reg-bsp" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
        <div><label class="mo-label">Secourisme</label><input type="number" min="0" id="rp-reg-sec" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
        <div><label class="mo-label">Élite</label><input type="number" min="0" id="rp-reg-elite" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
        <div><label class="mo-label">Drone</label><input type="number" min="0" id="rp-reg-drone" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
      </div>

      <div class="rp-section-title">⚠️ Plaintes & escalades</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px;">
        <div><label class="mo-label">Plaintes reçues</label><input type="number" min="0" id="rp-complaints" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
        <div><label class="mo-label">Résolues en -30 min (%)</label><input type="number" min="0" max="100" id="rp-resolved-pct" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
        <div><label class="mo-label">Escalades au VP <span style="color:var(--g)">(objectif: 0)</span></label><input type="number" min="0" id="rp-escalations" class="rp-num" style="width:100%;box-sizing:border-box;" placeholder="0"/></div>
      </div>

      <div class="rp-section-title">📝 Observations de la semaine</div>
      <textarea id="rp-observations" class="rp-textarea" placeholder="Tendances remarquées, questions fréquentes, objections récurrentes..."></textarea>

      <div class="rp-section-title">🚧 Besoins / blocages</div>
      <textarea id="rp-blockers" class="rp-textarea" placeholder="Ce dont l'équipe a besoin pour mieux performer..."></textarea>

      <div class="rp-section-title">➕ Notes additionnelles</div>
      <textarea id="rp-notes" class="rp-textarea" placeholder="Tout ce qui est important et qui n'est pas couvert ci-dessus..."></textarea>

      <div style="display:flex;gap:10px;margin-top:20px;">
        <button class="btn btn-primary" onclick="submitWeeklyReport('${pid}','${cfg.agents.join(',')}')">✓ Soumettre le rapport</button>
        <button class="btn" onclick="viewPastReports('${pid}')">📊 Voir rapports passés</button>
        <button class="btn" onclick="closeReportModal()">Annuler</button>
      </div>
    </div>
  </div>`;
}

async function submitWeeklyReport(pid, agentsStr) {
  const agents = agentsStr.split(',');
  const g = id => parseInt(document.getElementById(id)?.value||'0')||0;
  const t = id => document.getElementById(id)?.value?.trim()||'';

  const report = {
    person_id: pid,
    week_start: document.getElementById('rp-week-start').value,
    week_end: document.getElementById('rp-week-end').value,
    calls_inbound_hamza:  g(`rp-in-${agents[0]}`),
    calls_inbound_lilia:  g(`rp-in-${agents[1]||'s2'}`),
    calls_inbound_sekou:  g(`rp-in-${agents[2]||'s3'}`),
    calls_outbound_hamza: g(`rp-out-${agents[0]}`),
    calls_outbound_lilia: g(`rp-out-${agents[1]||'s2'}`),
    calls_outbound_sekou: g(`rp-out-${agents[2]||'s3'}`),
    answer_rate:          g('rp-answer-rate'),
    reg_bsp:              g('rp-reg-bsp'),
    reg_secourisme:       g('rp-reg-sec'),
    reg_elite:            g('rp-reg-elite'),
    reg_drone:            g('rp-reg-drone'),
    complaints_total:     g('rp-complaints'),
    complaints_resolved_pct: g('rp-resolved-pct'),
    escalations_to_vp:    g('rp-escalations'),
    observations:         t('rp-observations'),
    blockers:             t('rp-blockers'),
    additional_notes:     t('rp-notes'),
    submitted_at:         new Date().toISOString()
  };

  const btn = document.querySelector('#rmo .btn-primary');
  if(btn){ btn.textContent='Saving…'; btn.disabled=true; }

  const ok = await dbSaveReport(report);
  if(ok){
    closeReportModal();
    // Show quick confirmation
    const flash = document.createElement('div');
    flash.style.cssText='position:fixed;bottom:24px;right:24px;background:#22c55e;color:#000;padding:12px 20px;border-radius:8px;font-weight:700;z-index:10000;font-size:13px;';
    flash.textContent='✓ Rapport soumis avec succès';
    document.body.appendChild(flash);
    setTimeout(()=>flash.remove(), 3000);
  } else {
    if(btn){ btn.textContent='Réessayer'; btn.disabled=false; }
    alert('Erreur lors de la sauvegarde. Réessaie.');
  }
}

async function viewPastReports(pid) {
  const reports = await dbLoadReports(pid);
  const mo = document.getElementById('rmo');

  if(!reports.length){
    mo.innerHTML=`<div class="mo-box" style="max-width:560px;">
      <div class="mo-head"><span>📊 Rapports passés</span><button class="mo-close" onclick="closeReportModal()">✕</button></div>
      <div class="mo-body" style="text-align:center;padding:40px;color:var(--td);">Aucun rapport soumis pour l'instant.</div>
    </div>`;
    return;
  }

  const rows = reports.map(r=>{
    const totalIn = (r.calls_inbound_hamza||0)+(r.calls_inbound_lilia||0)+(r.calls_inbound_sekou||0);
    const totalOut = (r.calls_outbound_hamza||0)+(r.calls_outbound_lilia||0)+(r.calls_outbound_sekou||0);
    const totalReg = (r.reg_bsp||0)+(r.reg_secourisme||0)+(r.reg_elite||0)+(r.reg_drone||0);
    return `<tr>
      <td style="white-space:nowrap;">${r.week_start} → ${r.week_end}</td>
      <td>${totalIn}</td><td>${totalOut}</td>
      <td>${r.answer_rate||0}%</td>
      <td>${totalReg}</td>
      <td>${r.complaints_total||0}</td>
      <td style="color:${(r.escalations_to_vp||0)>0?'var(--a)':'var(--g)'};">${r.escalations_to_vp||0}</td>
      <td><button class="btn" style="font-size:10px;padding:2px 8px;" onclick="viewReportDetail(${JSON.stringify(r).split('"').join('&quot;')})">Détails</button></td>
    </tr>`;
  }).join('');

  mo.innerHTML=`<div class="mo-box" style="max-width:800px;width:100%;max-height:90vh;overflow-y:auto;">
    <div class="mo-head"><span>📊 Rapports passés — SAC</span><button class="mo-close" onclick="closeReportModal()">✕</button></div>
    <div class="mo-body">
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead style="color:var(--td);">
          <tr>
            <th style="text-align:left;padding:6px;">Semaine</th>
            <th>Entrants</th><th>Sortants</th><th>Taux rép.</th>
            <th>Inscriptions</th><th>Plaintes</th><th>Escalades VP</th><th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="margin-top:16px;">
        <button class="btn" onclick="openWeeklyReport('${pid}')">← Nouveau rapport</button>
      </div>
    </div>
  </div>`;
}

function viewReportDetail(r) {
  if(typeof r === 'string') { try { r = JSON.parse(r); } catch(e){} }
  const mo = document.getElementById('rmo');
  mo.innerHTML=`<div class="mo-box" style="max-width:560px;width:100%;max-height:90vh;overflow-y:auto;">
    <div class="mo-head"><span>📋 Rapport ${r.week_start} → ${r.week_end}</span><button class="mo-close" onclick="closeReportModal()">✕</button></div>
    <div class="mo-body" style="font-size:13px;line-height:1.6;">
      <div class="rp-section-title">📞 Appels</div>
      <table class="rp-table"><thead><tr><th>Agent</th><th>Entrants</th><th>Sortants</th></tr></thead>
      <tbody>
        <tr><td>Hamza</td><td>${r.calls_inbound_hamza||0}</td><td>${r.calls_outbound_hamza||0}</td></tr>
        <tr><td>Lilia</td><td>${r.calls_inbound_lilia||0}</td><td>${r.calls_outbound_lilia||0}</td></tr>
        <tr><td>Sekou</td><td>${r.calls_inbound_sekou||0}</td><td>${r.calls_outbound_sekou||0}</td></tr>
      </tbody></table>
      <p style="color:var(--td);">Taux de réponse: <b>${r.answer_rate||0}%</b></p>

      <div class="rp-section-title">🎓 Inscriptions</div>
      <p>BSP: <b>${r.reg_bsp||0}</b> | Secourisme: <b>${r.reg_secourisme||0}</b> | Élite: <b>${r.reg_elite||0}</b> | Drone: <b>${r.reg_drone||0}</b></p>

      <div class="rp-section-title">⚠️ Plaintes & escalades</div>
      <p>Plaintes: <b>${r.complaints_total||0}</b> | Résolues -30min: <b>${r.complaints_resolved_pct||0}%</b> | Escalades VP: <b style="color:${(r.escalations_to_vp||0)>0?'var(--a)':'var(--g)'}">${r.escalations_to_vp||0}</b></p>

      ${r.observations?`<div class="rp-section-title">📝 Observations</div><p>${esc(r.observations)}</p>`:''}
      ${r.blockers?`<div class="rp-section-title">🚧 Besoins / blocages</div><p>${esc(r.blockers)}</p>`:''}
      ${r.additional_notes?`<div class="rp-section-title">➕ Notes additionnelles</div><p>${esc(r.additional_notes)}</p>`:''}

      <div style="margin-top:16px;">
        <button class="btn" onclick="viewPastReports('${r.person_id}')">← Retour aux rapports</button>
      </div>
    </div>
  </div>`;
}

function closeReportModal() {
  const mo = document.getElementById('rmo');
  if(mo){ mo.style.display='none'; mo.innerHTML=''; }
}
