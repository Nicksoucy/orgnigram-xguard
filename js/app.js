// ==================== VIEW SWITCHING ====================
function switchView(v,btn){
  currentView=v;
  document.querySelectorAll('.vtab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  render();
}

// ==================== INIT ====================
document.querySelectorAll('.mo').forEach(m=>{m.addEventListener('click',function(e){if(e.target===this){closeM();closeFM();}});});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeM();closeFM();}});

// Realtime subscription (non-blocking)
try {
  db.channel('org-changes')
    .on('postgres_changes',{event:'*',schema:'public',table:'people'},()=>loadFromSupabase().then(renderAll))
    .on('postgres_changes',{event:'*',schema:'public',table:'departments'},()=>loadFromSupabase().then(renderAll))
    .subscribe();
} catch(e){ console.warn('Realtime unavailable:', e.message); }

// Timeout fallback — never spin forever
const _loadTimeout = setTimeout(()=>{
  const ls = document.getElementById('loading-screen');
  if(ls && ls.style.display !== 'none'){
    ls.innerHTML=`<p style="color:#f87171;font-size:13px;font-family:'DM Sans',sans-serif;padding:20px;text-align:center;">Connection timeout.<br><button onclick="location.reload()" style="margin-top:12px;padding:8px 16px;background:#ff6b35;border:none;border-radius:6px;color:#fff;cursor:pointer;">Retry</button></p>`;
  }
}, 10000);

// Load from Supabase then render
loadFromSupabase().then(()=>{
  clearTimeout(_loadTimeout);
  try {
    document.getElementById('loading-screen').style.display='none';
    render();
  } catch(renderErr) {
    console.error('Render error:', renderErr);
    document.getElementById('loading-screen').innerHTML=`<p style="color:#f87171;font-size:13px;font-family:'DM Sans',sans-serif;padding:20px;text-align:center;">Render error: ${renderErr.message}<br><button onclick="location.reload()" style="margin-top:12px;padding:8px 16px;background:#ff6b35;border:none;border-radius:6px;color:#fff;cursor:pointer;">Reload</button></p>`;
  }
}).catch(err=>{
  clearTimeout(_loadTimeout);
  console.error('Init load error:',err);
  document.getElementById('loading-screen').innerHTML=`<p style="color:#f87171;font-size:13px;font-family:'DM Sans',sans-serif;padding:20px;text-align:center;">Failed to connect: ${err.message}<br><button onclick="location.reload()" style="margin-top:12px;padding:8px 16px;background:#ff6b35;border:none;border-radius:6px;color:#fff;cursor:pointer;">Reload</button></p>`;
});
