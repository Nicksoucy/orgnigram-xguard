// ==================== RENDER ====================
function render(){
  const ct=document.getElementById('content');
  const cl=document.getElementById('controls');

  if(currentView==='dept') renderDept(ct,cl);
  else if(currentView==='tree') renderTree(ct,cl);
  else if(currentView==='canvas') renderCanvas(ct,cl);
  else if(currentView==='tasks') renderTasks(ct,cl);
  else if(currentView==='reports') renderReports(ct,cl);
  else if(currentView==='horaires') renderHoraires(ct,cl);
  else if(currentView==='schedule') renderSchedule(ct,cl);
  else renderFuture(ct,cl);

  renderSummary();
}

function cardHTML(p){
  const tags=p.programs.map(pr=>`<span class="tp ${TC[pr]||'t-bsp'}">${pr}</span>`).join('');
  return `<div class="card" onclick="openEdit('${p.id}')">
    <span class="badge ${bc(p.type)}">${bl(p.type)}</span>
    <div class="name" style="margin-top:3px;">${esc(p.name)}</div>
    <div class="role-line">${esc(p.role)}</div>
    <div class="meta"><div style="margin-bottom:2px;">${tags}</div>
    <span>🕐 ${esc(p.schedule)}</span> <span>${di(p.delegatable)}</span></div>
    ${p.notes?`<div class="note-line">📝 ${esc(p.notes)}</div>`:''}
  </div>`;
}

function renderSummary(){
  const t=data.length;
  const directToVP=data.filter(p=>p.reportsTo==='vp').length;
  document.getElementById('sum').innerHTML=`
    <div class="stat"><div class="d" style="background:var(--a)"></div><b>${t+1}</b><span style="color:var(--td)">Total</span></div>
    <div class="stat"><div class="d" style="background:var(--g)"></div><b>${data.filter(p=>p.type==='lead').length}</b><span style="color:var(--td)">Leads</span></div>
    <div class="stat"><div class="d" style="background:var(--bl)"></div><b>${data.filter(p=>p.type==='employee').length}</b><span style="color:var(--td)">Employees</span></div>
    <div class="stat"><div class="d" style="background:var(--p)"></div><b>${data.filter(p=>p.type==='contractor').length}</b><span style="color:var(--td)">Contractors</span></div>
    <div class="stat" style="margin-left:auto;"><div class="d" style="background:var(--r)"></div><b>${directToVP}</b><span style="color:var(--td)">Report to YOU directly</span></div>
  `;
}

function renderAll(){ render(); }
