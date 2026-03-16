const https = require('https');
const SUPABASE_HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function req(method, path, body, extra) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: SUPABASE_HOST,
      path: '/rest/v1/' + path,
      method,
      headers: {
        'apikey': KEY,
        'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
        ...(data ? { 'Content-Length': Buffer.byteLength(data) } : {}),
        ...(extra || {})
      }
    };
    const r = https.request(opts, res => {
      let b = '';
      res.on('data', d => b += d);
      res.on('end', () => resolve({ status: res.statusCode, body: b }));
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

// Parse an array that may contain JSON-encoded strings
function parseArr(arr) {
  if (!Array.isArray(arr)) return [];
  return arr.map(x => {
    if (typeof x === 'string') {
      try { return JSON.parse(x); } catch (e) { return null; }
    }
    return x;
  }).filter(x => x && typeof x === 'object' && x.text);
}

async function run() {
  // Fetch all tasks
  const r = await req('GET', 'tasks?select=*');
  const all = JSON.parse(r.body);
  console.log('Total rows fetched:', all.length);

  // Deduplicate by person_id
  const map = {};
  for (const row of all) map[row.person_id] = row;
  const unique = Object.values(map);
  console.log('Unique person_ids:', unique.length);

  // Check if data is string-encoded
  const sample = unique[0];
  const sampleTasks = sample.tasks || [];
  console.log('Sample first task type:', typeof sampleTasks[0]);
  console.log('Sample first task value:', JSON.stringify(sampleTasks[0]).substring(0, 80));

  // Clean: parse any string-encoded items
  const clean = unique.map(row => ({
    person_id: row.person_id,
    tasks: parseArr(row.tasks),
    outcomes: parseArr(row.outcomes),
    expected_outcomes: parseArr(row.expected_outcomes)
  }));

  // Show what we're about to save
  const sample2 = clean.find(r => r.person_id === 'v1');
  if (sample2) {
    console.log('Heidys outcomes after fix:', JSON.stringify(sample2.outcomes).substring(0, 150));
    console.log('Heidys expected after fix:', JSON.stringify(sample2.expected_outcomes[0]).substring(0, 100));
  }

  // Delete all existing rows
  const del = await req('DELETE', 'tasks?person_id=neq.NONE__');
  console.log('Delete status:', del.status);

  // Re-insert cleaned rows
  const ins = await req('POST', 'tasks', clean);
  console.log('Insert status:', ins.status, ins.body ? ins.body.substring(0, 100) : 'OK');
}

run().catch(console.error);
