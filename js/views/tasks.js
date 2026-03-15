// ==================== VIEW: TASKS & OUTCOMES ====================
function tkData(id){ if(!tasksData[id]) tasksData[id]={tasks:[],outcomes:[],expectedOutcomes:[]}; if(!tasksData[id].expectedOutcomes) tasksData[id].expectedOutcomes=[]; return tasksData[id]; }

function renderTasks(ct,cl){
  cl.innerHTML=`
    <div class="tasks-filters">
      <input id="tk-search" placeholder="Search people…" oninput="tkSetFilter(this.value)" value="${esc(_tkFilter)}"/>
      <select onchange="tkSetDept(this.value)">
        <option value="all" ${_tkDept==='all'?'selected':''}>All Departments</option>
        <option value="training" ${_tkDept==='training'?'selected':''}>Training</option>
        <option value="sac" ${_tkDept==='sac'?'selected':''}>Service à la clientèle</option>
        <option value="marketing" ${_tkDept==='marketing'?'selected':''}>Marketing</option>
        <option value="sales" ${_tkDept==='sales'?'selected':''}>Sales</option>
      </select>
      <span style="flex:1"></span>
      <button class="btn" onclick="expTasksJSON()">Export JSON</button>
    </div>`;

  const all=[VP,...data];
  const filtered=all.filter(p=>{
    const matchName=p.name.toLowerCase().includes(_tkFilter.toLowerCase())||p.role.toLowerCase().includes(_tkFilter.toLowerCase());
    const matchDept=_tkDept==='all'||p.dept===_tkDept||(_tkDept==='training'&&p.id==='vp');
    return matchName&&matchDept;
  });

  // progress bar across all tasks
  const allTasks=Object.values(tasksData).flatMap(d=>d.tasks||[]);
  const done=allTasks.filter(t=>t.done).length;
  const total=allTasks.length;
  const pct=total?Math.round(done/total*100):0;

  let html=`<div class="tasks-progress">
    <span style="color:var(--td);">Overall tasks</span>
    <div class="tp-bar"><div class="tp-fill" style="width:${pct}%"></div></div>
    <span class="tp-label">${done}/${total} done (${pct}%)</span>
  </div>
  <div class="tasks-grid">`;

  filtered.forEach(p=>{
    const d=tkData(p.id);
    const col=avatarColor(p.id);
    const cls=p.id==='vp'?'tk-vp':p.type==='lead'?'tk-lead':'';
    const doneCnt=d.tasks.filter(t=>t.done).length;
    const totalCnt=d.tasks.length;
    const pctP=totalCnt?Math.round(doneCnt/totalCnt*100):0;

    const tasksHTML=d.tasks.length
      ? d.tasks.map(t=>`
        <div class="tk-item">
          <input type="checkbox" ${t.done?'checked':''} onchange="tkToggle('${p.id}','${t.id}',this.checked)"/>
          <span class="tk-item-text${t.done?' done':''}" onclick="tkEditItem('${p.id}','${t.id}','task')">${esc(t.text)}</span>
          <span class="tk-del" onclick="tkDelItem('${p.id}','${t.id}','task')">×</span>
        </div>`).join('')
      : `<div class="tk-empty">No tasks yet</div>`;

    const outcomesHTML=d.outcomes.length
      ? d.outcomes.map(o=>`
        <div class="tk-outcome">
          <span class="tk-o-icon">◆</span>
          <span class="tk-o-text" onclick="tkEditItem('${p.id}','${o.id}','outcome')">${esc(o.text)}</span>
          <span class="tk-del" onclick="tkDelItem('${p.id}','${o.id}','outcome')">×</span>
        </div>`).join('')
      : `<div class="tk-empty">None defined yet</div>`;

    // Expected by VP — only shown on non-VP cards
    const expHTML= p.id!=='vp' ? (d.expectedOutcomes.length
      ? d.expectedOutcomes.map(o=>`
        <div class="tk-expected">
          <span class="tk-o-icon">◇</span>
          <span class="tk-o-text" onclick="tkEditItem('${p.id}','${o.id}','expected')">${esc(o.text)}</span>
          <span class="tk-del" onclick="tkDelItem('${p.id}','${o.id}','expected')">×</span>
        </div>`).join('')
      : `<div class="tk-empty">Nothing set yet</div>`) : null;

    html+=`<div class="tk-card ${cls}" id="tkc-${p.id}">
      <div class="tk-head">
        <div class="tk-avatar" style="background:${col};">${initials(p.name)}</div>
        <div class="tk-head-info">
          <div class="tk-head-name">${esc(p.name)}</div>
          <div class="tk-head-role">${esc(p.role)}</div>
        </div>
        ${totalCnt?`<span style="font-family:'Space Mono',monospace;font-size:9px;color:${pctP===100?'var(--g)':'var(--td)'};">${pctP}%</span>`:''}
      </div>
      <div class="tk-body">
        <div class="tk-section">
          <div class="tk-label">Tasks
            <span class="tk-add" onclick="tkAddInline('${p.id}','task')" title="Add task">＋</span>
          </div>
          <div id="tklist-${p.id}">${tasksHTML}</div>
          <div id="tkinput-${p.id}-task"></div>
        </div>
        <div class="tk-section">
          <div class="tk-label" style="color:var(--g);">◆ Their Outcomes
            <span class="tk-add" onclick="tkAddInline('${p.id}','outcome')" title="Add outcome">＋</span>
          </div>
          <div id="tklist-${p.id}-out">${outcomesHTML}</div>
          <div id="tkinput-${p.id}-outcome"></div>
        </div>
        ${expHTML!==null?`
        <hr class="tk-section-divider"/>
        <div class="tk-section">
          <div class="tk-label" style="color:var(--y);">◇ Expected by VP
            <span class="tk-add" onclick="tkAddInline('${p.id}','expected')" title="Add expectation">＋</span>
          </div>
          <div id="tklist-${p.id}-exp">${expHTML}</div>
          <div id="tkinput-${p.id}-expected"></div>
        </div>`:''}
      </div>
    </div>`;
  });

  html+=`</div>`;
  ct.innerHTML=html;
}

function tkSetFilter(v){ _tkFilter=v; renderTasks(document.getElementById('content'),document.getElementById('controls')); }
function tkSetDept(v){ _tkDept=v; renderTasks(document.getElementById('content'),document.getElementById('controls')); }

function tkToggle(pid,tid,checked){
  const d=tkData(pid);
  const t=d.tasks.find(x=>x.id===tid);
  if(t){ t.done=checked; dbSaveTasks(pid,d); renderTasks(document.getElementById('content'),document.getElementById('controls')); }
}

function tkAddInline(pid,kind){
  const slotId=`tkinput-${pid}-${kind}`;
  const slot=document.getElementById(slotId);
  if(!slot||slot.querySelector('input')) return;
  const inp=document.createElement('input');
  inp.className='tk-inline-input';
  const ph={task:'New task…',outcome:'Their outcome…',expected:'Expected by VP…'};
  inp.placeholder=ph[kind]||'New item…';
  inp.onkeydown=e=>{
    if(e.key==='Enter'&&inp.value.trim()){
      const d=tkData(pid);
      const newItem={id:gTaskId(),text:inp.value.trim()};
      if(kind==='task'){newItem.done=false;d.tasks.push(newItem);}
      else if(kind==='outcome') d.outcomes.push(newItem);
      else d.expectedOutcomes.push(newItem);
      dbSaveTasks(pid,d);
      renderTasks(document.getElementById('content'),document.getElementById('controls'));
    }
    if(e.key==='Escape') slot.innerHTML='';
  };
  inp.onblur=()=>{ setTimeout(()=>{ if(slot) slot.innerHTML=''; },200); };
  slot.appendChild(inp);
  inp.focus();
}

function tkEditItem(pid,iid,kind){
  const d=tkData(pid);
  const arr=kind==='task'?d.tasks:kind==='outcome'?d.outcomes:d.expectedOutcomes;
  const item=arr.find(x=>x.id===iid);
  if(!item) return;
  const listId=kind==='task'?`tklist-${pid}`:kind==='outcome'?`tklist-${pid}-out`:`tklist-${pid}-exp`;
  const list=document.getElementById(listId);
  if(!list) return;
  const el=list.querySelector(`.tk-item-text[onclick*="${iid}"], .tk-o-text[onclick*="${iid}"]`);
  if(!el||el.querySelector('input')) return;
  const orig=item.text;
  const inp=document.createElement('input');
  inp.className='tk-inline-input';
  inp.value=orig;
  inp.style.marginTop='0';
  el.replaceWith(inp);
  inp.focus(); inp.select();
  inp.onkeydown=e=>{
    if(e.key==='Enter'){
      item.text=inp.value.trim()||orig;
      dbSaveTasks(pid,tkData(pid));
      renderTasks(document.getElementById('content'),document.getElementById('controls'));
    }
    if(e.key==='Escape') renderTasks(document.getElementById('content'),document.getElementById('controls'));
  };
  inp.onblur=()=>{ item.text=inp.value.trim()||orig; dbSaveTasks(pid,tkData(pid)); renderTasks(document.getElementById('content'),document.getElementById('controls')); };
}

function tkDelItem(pid,iid,kind){
  const d=tkData(pid);
  if(kind==='task') d.tasks=d.tasks.filter(x=>x.id!==iid);
  else if(kind==='outcome') d.outcomes=d.outcomes.filter(x=>x.id!==iid);
  else d.expectedOutcomes=d.expectedOutcomes.filter(x=>x.id!==iid);
  dbSaveTasks(pid,d);
  renderTasks(document.getElementById('content'),document.getElementById('controls'));
}

function expTasksJSON(){
  const b=new Blob([JSON.stringify(tasksData,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='xguard-tasks.json';a.click();
}
