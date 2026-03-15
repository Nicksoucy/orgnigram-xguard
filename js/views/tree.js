// ==================== VIEW: HIERARCHY TREE ====================
function renderTree(ct,cl){
  cl.innerHTML=`<button class="btn primary" onclick="openAdd()">+ Add Person</button>
    <span style="flex:1"></span><button class="btn" onclick="expJSON()">Export JSON</button>`;

  function buildNode(person,isRoot){
    const children=getChildren(person.id);
    const cls=person.id==='vp'?'is-vp':person.type==='lead'?'is-lead':'';
    const childCount=children.length?`<span class="tc-count">${children.length} report${children.length>1?'s':''}</span>`:'';
    const tags=person.programs?person.programs.map(pr=>`<span class="tp ${TC[pr]||''}">${pr}</span>`).join(''):'';
    const onclick=person.id==='vp'?'':`onclick="openEdit('${person.id}')"`;

    let h=`<div class="${isRoot?'tree-root':'tree-item'}">`;
    if(!isRoot) h+=`<div class="tree-branch"></div>`;
    h+=`<div class="tree-card ${cls}" ${onclick}>
      <div class="tc-info">
        <span class="badge ${bc(person.type)}">${bl(person.type)}</span>
        <div class="tc-name" style="margin-top:2px;">${esc(person.name)}</div>
        <div class="tc-role">${esc(person.role||'')}</div>
        ${tags?`<div class="tc-tags">${tags}</div>`:''}
      </div>
      ${childCount} <span>${di(person.delegatable||'no')}</span>
    </div></div>`;

    if(children.length){
      h+=`<div class="tree-children">`;
      children.forEach(c=>{ h+=buildNode(c,false); });
      h+=`</div>`;
    }
    return h;
  }

  ct.innerHTML=`<div class="tree">${buildNode(VP,true)}</div>`;
}
