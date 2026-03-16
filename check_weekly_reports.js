const https = require('https');

const HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY  = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function req(method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const options = {
      hostname: HOST,
      path: path,
      method: method,
      headers: {
        'apikey': KEY,
        'Authorization': `Bearer ${KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      }
    };
    if (data) options.headers['Content-Length'] = Buffer.byteLength(data);
    const r = https.request(options, res => {
      let buf = '';
      res.on('data', d => buf += d);
      res.on('end', () => resolve({ status: res.statusCode, body: buf }));
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

async function main() {
  console.log('=== Checking weekly_reports table ===');
  const check = await req('GET', '/rest/v1/weekly_reports?limit=1', null);
  console.log(`GET /rest/v1/weekly_reports?limit=1 → ${check.status}`);
  console.log(`Body: ${check.body}`);

  if (check.status === 200) {
    console.log('\n✓ Table EXISTS. weekly_reports table is accessible.');
  } else if (check.status === 404 || check.status === 406 || check.body.includes('does not exist') || check.body.includes('relation')) {
    console.log('\n✗ Table does NOT exist (status ' + check.status + ')');
    console.log('\nTo create it, run the following SQL in Supabase Dashboard > SQL Editor:');
    console.log(`
CREATE TABLE IF NOT EXISTS weekly_reports (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id   text        REFERENCES people(id),
  week_start  date,
  week_end    date,
  report_type text,
  data        jsonb,
  notes       text,
  created_at  timestamptz DEFAULT now()
);
    `);
  } else {
    console.log(`\nUnexpected status ${check.status}. Check response above.`);
  }
}

main().catch(console.error);
