// ==================== VIEW: CANVAS ====================

// Global pan listeners — attached once
window.addEventListener('mousemove',e=>{
  if(!_cvDrag) return;
  _cvPanX=_cvDrag.px+(e.clientX-_cvDrag.sx);
  _cvPanY=_cvDrag.py+(e.clientY-_cvDrag.sy);
  _applyCV();
});
window.addEventListener('mouseup',()=>{
  _cvDrag=null;
  document.getElementById('canvas-wrap')?.classList.remove('dragging');
});

function cvBuildDivisions(){
  // Build one canvas division per department
  CV_DIVS=departments.map(dept=>({
    id:'div_'+dept.key,
    label:dept.label,
    color:dept.color,
    deptKey:dept.key,
    members:[]
  }));
}
cvBuildDivisions();

// Dynamically build members list & map from data each time
function cvBuildMembers(){
  cvBuildDivisions();
  const subChildIds=new Set(data.filter(p=>p.reportsTo&&p.reportsTo!=='vp').map(p=>p.id));
  CV_DIVS.forEach(d=>{
    d.members=data.filter(p=>p.dept===d.deptKey&&!subChildIds.has(p.id)).map(p=>p.id);
  });
  const map={};
  CV_DIVS.forEach(d=>d.members.forEach(m=>{map[m]=d.id;}));
  return map;
}
let CV_DIV_MAP=cvBuildMembers();

// get the canvas parent of a node (div node or vp)
function cvParent(id){
  const divId=CV_DIV_MAP[id];
  if(divId) return divId;
  // div nodes report to vp
  if(CV_DIVS.find(d=>d.id===id)) return 'vp';
  const p=getById(id);
  return p?.reportsTo||'vp';
}

// get children in custom order — supports division nodes
function cvChildren(pid){
  // vp's children = the division nodes
  if(pid==='vp'){
    const order=cvOrder['vp']||CV_DIVS.map(d=>d.id);
    return order.map(id=>CV_DIVS.find(d=>d.id===id)).filter(Boolean).map(d=>({id:d.id,_isDiv:true}));
  }
  // division node's children = its members
  const div=CV_DIVS.find(d=>d.id===pid);
  if(div){
    const memberObjs=div.members.map(m=>getById(m)).filter(Boolean);
    if(!cvOrder[pid]) return memberObjs;
    const ordered=cvOrder[pid].map(id=>memberObjs.find(c=>c.id===id)).filter(Boolean);
    const rest=memberObjs.filter(c=>!cvOrder[pid].includes(c.id));
    return [...ordered,...rest];
  }
  // regular person — children from data (e.g. L3 → s2,s3; m1 → m2)
  const ch=getChildren(pid);
  if(!cvOrder[pid]) return ch;
  const ordered=cvOrder[pid].map(id=>ch.find(c=>c.id===id)).filter(Boolean);
  const rest=ch.filter(c=>!cvOrder[pid].includes(c.id));
  return [...ordered,...rest];
}

// move a node left or right among its siblings
function cvMove(id,dir){
  const pid=cvParent(id);
  const siblings=cvChildren(pid);
  const order=siblings.map(s=>s.id);
  const i=order.indexOf(id); if(i===-1) return;
  const ni=i+dir;
  if(ni<0||ni>=order.length) return;
  [order[i],order[ni]]=[order[ni],order[i]];
  cvOrder[pid]=order;
  dbSaveCanvasOrder(pid,order);
  _cvInited=true;
  renderCanvas(document.getElementById('content'),document.getElementById('controls'));
}

function renderCanvas(ct,cl){
  CV_DIV_MAP=cvBuildMembers(); // refresh division memberships from data
  cl.innerHTML=`<button class="btn primary" onclick="openAdd()">+ Add Person</button>
    <span style="flex:1"></span>
    <button class="btn" onclick="cvExportPNG()" title="Export PNG" style="gap:4px;">🖼 PNG</button>
    <button class="btn" onclick="cvExportPDF()" title="Export PDF" style="gap:4px;">📄 PDF</button>
    <div class="cn-zoom">
      <button class="btn" onclick="cvZoom(0.15)">＋</button>
      <button class="btn" onclick="cvZoom(-0.15)">－</button>
      <button class="btn" onclick="cvReset()">Reset</button>
    </div>`;

  // ---- LAYOUT: VP top → divisions spread horizontally → members in columns below ----
  const NODE_W=160, NODE_H=185, GAP_X=24, GAP_Y=20;
  const DIV_H=48;
  const SUBCOL_WRAP=6;  // wrap into 2 sub-columns if > this many members
  const COL_GAP=60;     // gap between division columns
  const VP_DIV_GAP=80;
  const DIV_MEM_GAP=44;

  const divOrder=(cvOrder['vp']||CV_DIVS.map(d=>d.id))
    .map(id=>CV_DIVS.find(d=>d.id===id)).filter(Boolean);

  // Compute each division's rendered width based on sub-column count
  function divSubCols(div){
    return cvChildren(div.id).length > SUBCOL_WRAP ? 2 : 1;
  }
  function divRenderW(div){
    const sc=divSubCols(div);
    return sc===1 ? NODE_W : NODE_W*2+GAP_X;
  }

  // Sequential column x positions
  const colXs=[], colWs=[];
  let cx=0;
  divOrder.forEach(div=>{
    colXs.push(cx);
    const w=divRenderW(div);
    colWs.push(w);
    cx+=w+COL_GAP;
  });
  const totalW=cx-COL_GAP;

  const positions={};
  positions['vp']={x: totalW/2 - NODE_W/2, y: 0};

  const divY=NODE_H+VP_DIV_GAP;

  const divColData=[];
  divOrder.forEach((div,di)=>{
    const colX=colXs[di];
    const colW=colWs[di];
    const nSubCols=divSubCols(div);
    const members=cvChildren(div.id);

    // Lay members in nSubCols sub-columns
    const memStartY=divY+DIV_H+DIV_MEM_GAP;
    members.forEach((m,i)=>{
      const sc=i%nSubCols;  // which sub-column
      const row=Math.floor(i/nSubCols);
      const mx=colX+sc*(NODE_W+GAP_X);
      const my=memStartY+row*(NODE_H+GAP_Y);
      positions[m.id]={x:mx, y:my};
      // sub-children of m (e.g. Hatem under Alex) — stack below in same sub-column
      cvChildren(m.id).forEach((child,j)=>{
        // place below the last row of this sub-col
        const lastRow=Math.floor((members.length-1)/nSubCols);
        positions[child.id]={x:mx, y:memStartY+(lastRow+1+j)*(NODE_H+GAP_Y)};
      });
    });

    positions[div.id]={x:colX, y:divY, w:colW};
    divColData.push({div, colX, colW, members});
  });

  const allP=[VP,...data];
  allP.forEach(p=>{ if(!positions[p.id]) positions[p.id]={x:0,y:0}; });

  const xs=Object.values(positions).map(p=>p.x);
  const ys=Object.values(positions).map(p=>p.y);
  const minX=Math.min(...xs), maxX=Math.max(...xs)+NODE_W;
  const minY=Math.min(...ys), maxY=Math.max(...ys)+NODE_H;
  const W=maxX-minX+120, H=maxY-minY+120;
  const ox=-minX+60, oy=-minY+40;

  // build HTML nodes
  let nodesHTML='';

  // Render division nodes
  divOrder.forEach((div,di)=>{
    const pos=positions[div.id];
    if(!pos) return;
    const px=pos.x+ox, py=pos.y+oy;
    const memberCount=div.members.filter(m=>getById(m)).length;
    const canU=di>0, canD=di<divOrder.length-1;
    const arrows=`<div class="cn-arrows" onclick="event.stopPropagation()">
      <span class="cn-arr${canU?'':' disabled'}" onclick="${canU?`cvMove('${div.id}',-1)`:''}" title="Move left">◀</span>
      <span class="cn-arr${canD?'':' disabled'}" onclick="${canD?`cvMove('${div.id}',1)`:''}" title="Move right">▶</span>
    </div>`;
    nodesHTML+=`<div class="cn-div" id="cn-${div.id}" style="left:${px}px;top:${py}px;width:${pos.w}px;border-color:${div.color}30;background:${div.color}10;">
      <div class="cn-div-label" style="color:${div.color};">${div.label}</div>
      <div class="cn-div-count" style="color:${div.color};">${memberCount}</div>
      ${arrows}
    </div>`;
  });

  // Render person nodes
  allP.forEach(p=>{
    const pos=positions[p.id];
    if(!pos) return;
    const px=pos.x+ox, py=pos.y+oy;
    const cls=p.id==='vp'?'cn-vp':p.type==='lead'?'cn-lead':'';
    const col=avatarColor(p.id);
    const tags=p.programs?p.programs.slice(0,2).map(pr=>`<span class="tp ${TC[pr]||''}" style="font-size:7px;">${pr}</span>`).join(''):'';
    const editClick=p.id==='vp'?'':`onclick="openEdit('${p.id}')"`;

    // sibling arrows (up/down since layout is vertical)
    let arrows='';
    if(p.id!=='vp'){
      const pid=cvParent(p.id);
      const siblings=cvChildren(pid);
      const idx=siblings.findIndex(s=>s.id===p.id);
      const canU=idx>0, canD=idx<siblings.length-1;
      arrows=`<div class="cn-arrows" onclick="event.stopPropagation()">
        <span class="cn-arr${canU?'':' disabled'}" onclick="${canU?`cvMove('${p.id}',-1)`:''}" title="Move up">▲</span>
        <span class="cn-arr${canD?'':' disabled'}" onclick="${canD?`cvMove('${p.id}',1)`:''}" title="Move down">▼</span>
      </div>`;  // ▲▼ since members stack vertically within their column
    }

    nodesHTML+=`<div class="cn ${cls}" id="cn-${p.id}" style="left:${px}px;top:${py}px;" ${editClick}>
      <div class="cn-avatar" style="background:${col};">${initials(p.name)}</div>
      <div class="cn-name">${esc(p.name)}</div>
      <div class="cn-role">${esc(p.role||'')}</div>
      <div class="cn-badges">${tags}</div>
      <div class="cn-di">${di(p.delegatable||'unknown')}</div>
      ${arrows}
    </div>`;
  });

  // SVG connector lines
  let svgLines='';

  // VP → each division (bezier curve top-down)
  const vpPos=positions['vp'];
  const vpCx=vpPos.x+ox+NODE_W/2;
  const vpBy=vpPos.y+oy+NODE_H;
  divOrder.forEach(div=>{
    const cp=positions[div.id];
    if(!cp) return;
    const x2=cp.x+ox+cp.w/2, y2=cp.y+oy;
    const my=(vpBy+y2)/2;
    svgLines+=`<path d="M${vpCx},${vpBy} C${vpCx},${my} ${x2},${my} ${x2},${y2}"
      fill="none" stroke="${div.color}" stroke-width="2" stroke-opacity="0.6"/>`;
  });

  // Division → members: vertical line from div bottom to each member top
  divColData.forEach(({div,colW,members})=>{
    const dp=positions[div.id];
    if(!dp) return;
    const dx=dp.x+ox+colW/2, dy=dp.y+oy+DIV_H;
    members.forEach(m=>{
      const mp=positions[m.id];
      if(!mp) return;
      const x2=mp.x+ox+NODE_W/2, y2=mp.y+oy;
      svgLines+=`<path d="M${dx},${dy} L${dx},${y2} L${x2},${y2}"
        fill="none" stroke="${div.color}" stroke-width="1.5" stroke-opacity="0.45"/>`;

      // Member → sub-children (vertical, stacked below)
      const subCh=cvChildren(m.id);
      subCh.forEach(sc=>{
        const sp=positions[sc.id];
        if(!sp) return;
        const sx=mp.x+ox+NODE_W/2, sy=mp.y+oy+NODE_H;
        const tx=sp.x+ox+NODE_W/2, ty=sp.y+oy;
        svgLines+=`<path d="M${sx},${sy} L${sx},${(sy+ty)/2} L${tx},${(sy+ty)/2} L${tx},${ty}"
          fill="none" stroke="var(--ba)" stroke-width="1.5" stroke-opacity="0.4"/>`;
      });
    });
  });

  _cvBaseW=W; _cvBaseH=H;
  const wrapH=Math.max(600, window.innerHeight-180);
  ct.innerHTML=`<div id="canvas-wrap" style="height:${wrapH}px;">
    <div id="canvas-stage" style="width:${W}px;height:${H}px;">
      <svg id="canvas-svg" viewBox="0 0 ${W} ${H}" style="width:${W}px;height:${H}px;">${svgLines}</svg>
      ${nodesHTML}
    </div>
  </div>`;

  // Center on first open
  const wrap=document.getElementById('canvas-wrap');
  if(!_cvInited){
    _cvInited=true;
    requestAnimationFrame(()=>{
      const ww=wrap.offsetWidth, wh=wrap.offsetHeight;
      _cvPanX=(ww - W*_cvZoom)/2;
      _cvPanY=20;
      _applyCV();
    });
  } else {
    _applyCV();
  }

  // drag-to-pan
  wrap.addEventListener('mousedown',e=>{
    if(e.target.closest('.cn')||e.target.closest('.cn-div')) return;
    _cvDrag={sx:e.clientX,sy:e.clientY,px:_cvPanX,py:_cvPanY};
    wrap.classList.add('dragging');
  });

  // wheel zoom (pivot at cursor)
  wrap.addEventListener('wheel',e=>{
    e.preventDefault();
    const delta=e.deltaY>0?-0.08:0.08;
    const rect=wrap.getBoundingClientRect();
    const mx=e.clientX-rect.left;
    const my=e.clientY-rect.top;
    const oldZ=_cvZoom;
    _cvZoom=Math.max(0.15,Math.min(2.5,_cvZoom+delta));
    // keep point under cursor fixed
    _cvPanX=mx-(mx-_cvPanX)*(_cvZoom/oldZ);
    _cvPanY=my-(my-_cvPanY)*(_cvZoom/oldZ);
    _applyCV();
  },{passive:false});
}

function _applyCV(){
  const stage=document.getElementById('canvas-stage');
  if(stage) stage.style.transform=`translate(${_cvPanX}px,${_cvPanY}px) scale(${_cvZoom})`;
}
function cvZoom(d){
  const wrap=document.getElementById('canvas-wrap');
  if(!wrap) return;
  const ww=wrap.offsetWidth/2, wh=wrap.offsetHeight/2;
  const oldZ=_cvZoom;
  _cvZoom=Math.max(0.15,Math.min(2.5,_cvZoom+d));
  _cvPanX=ww-(ww-_cvPanX)*(_cvZoom/oldZ);
  _cvPanY=wh-(wh-_cvPanY)*(_cvZoom/oldZ);
  _applyCV();
}
function cvReset(){ _cvZoom=0.72; _cvPanX=0; _cvPanY=20; _cvInited=false; cvOrder={}; renderCanvas(document.getElementById('content'),document.getElementById('controls')); }

// ── Export helpers ──────────────────────────────────────────
async function _cvCapture() {
  const stage = document.getElementById('canvas-stage');
  if (!stage) return null;
  // Temporarily reset transform so html2canvas captures full diagram
  const saved = stage.style.transform;
  stage.style.transform = 'translate(0px,0px) scale(1)';
  await new Promise(r => requestAnimationFrame(r)); // let browser repaint
  const canvas = await html2canvas(stage, {
    backgroundColor: '#0c0c0f',
    scale: 1.5,           // 1.5× for crisp output
    useCORS: true,
    logging: false,
  });
  stage.style.transform = saved;
  return canvas;
}

async function cvExportPNG() {
  const btn = document.querySelector('[onclick="cvExportPNG()"]');
  if (btn) { btn.textContent = '⏳ Export…'; btn.disabled = true; }
  try {
    const canvas = await _cvCapture();
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `xguard-org-chart-${new Date().toISOString().slice(0,10)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } finally {
    if (btn) { btn.textContent = '🖼 PNG'; btn.disabled = false; }
  }
}

async function cvExportPDF() {
  const btn = document.querySelector('[onclick="cvExportPDF()"]');
  if (btn) { btn.textContent = '⏳ Export…'; btn.disabled = true; }
  try {
    const canvas = await _cvCapture();
    if (!canvas) return;
    const { jsPDF } = window.jspdf;
    const imgW = canvas.width, imgH = canvas.height;
    // Landscape page sized to the diagram (in mm at 96dpi → px/3.7795)
    const pxToMm = px => px / 3.7795;
    const pdf = new jsPDF({
      orientation: imgW > imgH ? 'landscape' : 'portrait',
      unit: 'mm',
      format: [pxToMm(imgW), pxToMm(imgH)],
    });
    pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, pxToMm(imgW), pxToMm(imgH));
    pdf.save(`xguard-org-chart-${new Date().toISOString().slice(0,10)}.pdf`);
  } finally {
    if (btn) { btn.textContent = '📄 PDF'; btn.disabled = false; }
  }
}
