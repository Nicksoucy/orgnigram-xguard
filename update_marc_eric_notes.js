const https = require('https');
const HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function req(method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: HOST, path: '/rest/v1/' + path, method,
      headers: {
        'apikey': KEY, 'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json', 'Prefer': 'return=minimal',
        ...(data ? {'Content-Length': Buffer.byteLength(data)} : {})
      }
    };
    const r = https.request(opts, res => {
      let b = ''; res.on('data', d => b += d);
      res.on('end', () => resolve({status: res.statusCode, body: b}));
    });
    r.on('error', reject);
    if (data) r.write(data); r.end();
  });
}

async function run() {
  const notes = `[Mars 2026 — NOTE VP] Situation à clarifier. Marc-Éric est fiable et compétent — probablement intéressé par plus de responsabilités, mais VP pas encore certain de vouloir en donner davantage. Rôle clé dans Élite aux côtés de Dom. Question ouverte : est-ce que Dom devient son patron pour la gestion Élite, et Marc-Éric reste à 1 jour/semaine + on remplit le reste avec d'autres choses? Situation délicate — ne pas prendre de décision précipitée. À revoir lors du mapping des tâches VP et de la conversation formelle avec Marc-Éric.`;

  const r = await req('PATCH', 'people?id=eq.t3', { notes });
  console.log('Updated Marc-Eric notes:', r.status, r.body || 'OK');
}
run().catch(console.error);
