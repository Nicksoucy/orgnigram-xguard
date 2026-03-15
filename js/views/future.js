// ==================== VIEW: FUTURE STATE ====================
function renderFuture(ct,cl){
  cl.innerHTML=`<button class="btn future-btn" onclick="openFM()">+ Plan a Change</button>
    <span style="flex:1"></span><button class="btn" onclick="expFutureJSON()">Export Future Plan</button>`;

  // Current hierarchy (left)
  function miniTree(pid,depth){
    const children=getChildren(pid);
    let h='';
    children.forEach(c=>{
      const fc=futureChanges.find(f=>f.personId===c.id);
      const changed=fc?'border-color:var(--cy);':'';
      h+=`<div style="margin-left:${depth*20}px;margin-bottom:6px;">
        <div class="future-person" style="${changed}" onclick="openEdit('${c.id}')">
          <span class="badge ${bc(c.type)}" style="flex-shrink:0;">${bl(c.type)}</span>
          <div style="flex:1;"><div class="fp-name">${esc(c.name)}</div><div class="fp-role">${esc(c.role)}</div></div>
          <span>${di(c.delegatable)}</span>
        </div>
        ${miniTree(c.id,depth+1)}
      </div>`;
    });
    return h;
  }

  // Future changes list (right)
  let changesHTML='';
  if(futureChanges.length===0){
    changesHTML=`<div class="empty">No changes planned yet.<br><br>Click "+ Plan a Change" to start building your future org structure.<br><br>
      Think about:<br>• Who should trainers report to instead of you?<br>• Can Marc Éric or Marie-Claude become leads?<br>• What outcomes can Hamza own?</div>`;
  } else {
    futureChanges.forEach((fc,i)=>{
      const p=getById(fc.personId);
      const curManager=getById(p.reportsTo)||VP;
      const futManager=getById(fc.futureReportsTo)||VP;
      changesHTML+=`<div class="future-change" onclick="editFChange(${i})" style="cursor:pointer;">
        <div class="fc-name">${esc(p.name)}</div>
        ${fc.futureReportsTo!==p.reportsTo?`<div class="fc-label">Reports To</div>
          <div class="fc-from">Currently: ${esc(curManager.name)}</div>
          <div class="fc-to">→ Future: ${esc(futManager.name)}</div>`:''}
        ${fc.futureRole&&fc.futureRole!==p.role?`<div class="fc-label" style="margin-top:6px;">Role</div>
          <div class="fc-from">Currently: ${esc(p.role)}</div>
          <div class="fc-to">→ Future: ${esc(fc.futureRole)}</div>`:''}
        ${fc.futureType&&fc.futureType!==p.type?`<div class="fc-label" style="margin-top:6px;">Type</div>
          <div class="fc-from">Currently: ${bl(p.type)}</div>
          <div class="fc-to">→ Future: ${bl(fc.futureType)}</div>`:''}
        ${fc.notes?`<div style="margin-top:6px;font-size:10px;color:var(--td);font-style:italic;">💡 ${esc(fc.notes)}</div>`:''}
      </div>`;
    });
  }

  ct.innerHTML=`<div class="future-container">
    <div class="future-col">
      <div class="future-col-header">
        <h3>Current State</h3><span class="state-badge state-current">Now</span>
      </div>
      <div class="future-col-body">
        <div class="future-person" style="border-color:var(--a);">
          <span class="badge b-exec">VP</span>
          <div style="flex:1;"><div class="fp-name">You</div><div class="fp-role">VP of Training</div></div>
          <span class="tc-count">${getChildren('vp').length} direct</span>
        </div>
        ${miniTree('vp',1)}
      </div>
    </div>
    <div class="future-col">
      <div class="future-col-header">
        <h3>Planned Changes</h3><span class="state-badge state-future">${futureChanges.length} change${futureChanges.length!==1?'s':''}</span>
      </div>
      <div class="future-col-body">${changesHTML}</div>
    </div>
  </div>`;
}
