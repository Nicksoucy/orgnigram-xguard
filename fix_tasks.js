const https = require('https');
const SUPABASE_HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function req(method, path, body, extraHeaders={}) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: SUPABASE_HOST, path: '/rest/v1/' + path, method,
      headers: {'apikey': KEY, 'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json', 'Prefer': 'return=minimal',
        ...(data ? {'Content-Length': Buffer.byteLength(data)} : {}), ...extraHeaders}
    };
    const r = https.request(opts, res => {
      let b = ''; res.on('data', d => b += d);
      res.on('end', () => resolve({status: res.statusCode, body: b}));
    });
    r.on('error', reject);
    if (data) r.write(data); r.end();
  });
}

function parseArr(arr) {
  if (!Array.isArray(arr)) return [];
  return arr.map(x => {
    if (typeof x === 'string') { try { return JSON.parse(x); } catch(e) { return {id: 'x_'+Math.random().toString(36).slice(2), text: x}; } }
    return x;
  }).filter(x => x && (x.text || x.id));
}

async function run() {
  // Get all tasks
  const r = await req('GET', 'tasks?select=*', null);
  const all = JSON.parse(r.body);
  console.log('Total rows:', all.length);

  // Deduplicate: keep last per person_id (has most recent data)
  const map = {};
  for (const row of all) map[row.person_id] = row;
  const unique = Object.values(map);
  console.log('Unique people:', unique.length);

  // Delete all rows
  const del = await req('DELETE', 'tasks?person_id=neq.PLACEHOLDER', null, {'Prefer':'return=minimal'});
  console.log('Delete all:', del.status);

  // Re-insert cleaned
  const clean = unique.map(row => ({
    person_id: row.person_id,
    tasks: parseArr(row.tasks),
    outcomes: parseArr(row.outcomes),
    expected_outcomes: parseArr(row.expected_outcomes)
  }));

  const ins = await req('POST', 'tasks', clean, {'Prefer':'return=minimal'});
  console.log('Re-insert', clean.length, 'rows:', ins.status, ins.body || 'OK');
}
run().catch(console.error);
