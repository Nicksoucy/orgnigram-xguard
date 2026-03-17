const https = require('https');
const fs = require('fs');

const HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';
const SERVICE_KEY = 'sb_secret_ZY7VEdxpvpeTbTNpytlxHw_NODyHgnO';

// Split schema into individual statements and run them via RPC
function req(method, path, body, useService=false) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: HOST, path, method,
      headers: {
        'apikey': useService ? SERVICE_KEY : KEY,
        'Authorization': 'Bearer ' + (useService ? SERVICE_KEY : KEY),
        'Content-Type': 'application/json',
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
  const sql = fs.readFileSync('C:/Users/nicol/orgnigram-xguard/schedule_schema.sql', 'utf8');
  
  // Try running via Supabase SQL endpoint
  const r = await req('POST', '/rest/v1/rpc/exec_sql', {sql}, true);
  console.log('RPC exec_sql:', r.status, r.body.slice(0,200));
  
  // Verify tables exist by checking each one
  const tables = ['locations','cohorts','schedule_entries','schedule_templates','availabilities','replacements'];
  for (const t of tables) {
    const check = await req('GET', `/rest/v1/${t}?select=id&limit=1`, null, false);
    console.log(`Table ${t}:`, check.status === 200 ? '✅ exists' : `❌ ${check.status} ${check.body.slice(0,100)}`);
  }
}
run().catch(console.error);
