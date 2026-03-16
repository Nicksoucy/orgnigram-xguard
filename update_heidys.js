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

async function run() {
  // Update Heidys notes in people table
  const personUpdate = {
    notes: '⚠️ 3 choses à régler: (1) Doit utiliser GHL pour TOUS les appels — pas encore le cas. (2) Doit reporter à Jessica ou Mitchell — plus au VP. (3) Targets à définir après 3-4 semaines de baseline. Payée 20h/semaine max. Vend: BSP, Secourisme, Élite. Leads qualifiés via formulaire site (TikTok, Google, Instagram).',
  };
  const r1 = await req('PATCH', 'people?id=eq.v1', personUpdate);
  console.log('Update person notes:', r1.status, r1.body || 'OK');

  // Update tasks/outcomes for Heidys
  const tasksUpdate = {
    tasks: [
      { id: 'tk_v1a', text: '⚠️ À RÉGLER: Migrer 100% des appels et suivis dans GHL — zéro appel hors système', done: false },
      { id: 'tk_v1b', text: '⚠️ À RÉGLER: Identifier son responsable direct (Jessica ou Mitchell) — plus reporter au VP', done: false },
      { id: 'tk_v1c', text: 'Établir baseline sur 3-4 semaines: nombre appels/semaine, taux conversion, formations vendues', done: false },
      { id: 'tk_v1d', text: 'Soumettre rapport KPI chaque vendredi', done: false }
    ],
    outcomes: [
      { id: 'o_v1a', text: 'Appels sortants sur leads qualifiés (formulaire site — TikTok, Google, Instagram)' },
      { id: 'o_v1b', text: 'Vend formations: BSP Gardiennage, Secourisme, Élite' },
      { id: 'o_v1c', text: 'Gère les 1ers appels, 2e appels, 3e appels+ et suivis' },
      { id: 'o_v1d', text: 'Payée 20h/semaine — peut travailler plus mais 20h max remboursées' }
    ],
    expected_outcomes: [
      { id: 'e_v1a', text: '🚧 EN ÉTABLISSEMENT — KPI hebdo chaque vendredi: appels 1ers, 2e appels, 3e appels+, inscriptions conclues (+ quelle formation), heures travaillées, % appels logués dans GHL' },
      { id: 'e_v1b', text: '🚧 EN ÉTABLISSEMENT — Targets à définir après 3-4 semaines de baseline (appels min/semaine, taux conversion, inscriptions/semaine)' },
      { id: 'e_v1c', text: '100% des interactions logées dans GHL — zéro appel hors système' },
      { id: 'e_v1d', text: 'Reporter à Jessica ou Mitchell — plus jamais directement au VP' },
      { id: 'e_v1e', text: 'Drone à intégrer dans quelques semaines — à définir lors de la prochaine révision' }
    ]
  };

  const r2 = await req('PATCH', 'tasks?person_id=eq.v1', tasksUpdate);
  console.log('Update tasks:', r2.status, r2.body || 'OK');
}

run().catch(console.error);
