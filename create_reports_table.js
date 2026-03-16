const https = require('https');
const SUPABASE_HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
// Using service role key for DDL operations via REST
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

// Test insert to see if table exists
function req(method, path, body) {
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
        ...(data ? { 'Content-Length': Buffer.byteLength(data) } : {})
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

async function run() {
  // Try to select from weekly_reports to see if it exists
  const r = await req('GET', 'weekly_reports?select=id&limit=1');
  console.log('Table check status:', r.status);
  if (r.status === 200) {
    console.log('Table already exists!');
  } else {
    console.log('Table does not exist yet. Response:', r.body);
    console.log('\nYou need to run this SQL in Supabase Dashboard > SQL Editor:');
    console.log(`
CREATE TABLE IF NOT EXISTS weekly_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  person_id TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  -- Call stats
  calls_inbound_hamza INT DEFAULT 0,
  calls_inbound_lilia INT DEFAULT 0,
  calls_inbound_sekou INT DEFAULT 0,
  calls_outbound_hamza INT DEFAULT 0,
  calls_outbound_lilia INT DEFAULT 0,
  calls_outbound_sekou INT DEFAULT 0,
  answer_rate INT DEFAULT 0,
  -- Registrations
  reg_bsp INT DEFAULT 0,
  reg_secourisme INT DEFAULT 0,
  reg_elite INT DEFAULT 0,
  reg_drone INT DEFAULT 0,
  -- Issues
  complaints_total INT DEFAULT 0,
  complaints_resolved_pct INT DEFAULT 0,
  escalations_to_vp INT DEFAULT 0,
  -- Free text
  observations TEXT DEFAULT '',
  blockers TEXT DEFAULT '',
  additional_notes TEXT DEFAULT '',
  -- Meta
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
    `);
  }
}
run().catch(console.error);
