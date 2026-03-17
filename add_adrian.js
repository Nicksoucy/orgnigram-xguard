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
  // Add Adrian
  const adrian = {
    id: 'c1',
    name: 'Adrian Codreanu',
    role: 'Création de contenu — Filming, Script & Editing',
    dept: 'marketing',
    type: 'contractor',
    reports_to: 'm1',
    programs: [],
    schedule: 'Mensuel — 10 vidéos/mois (scripts + filming + editing)',
    delegate: false,
    notes: 'ac.prods.inc@gmail.com — Objectif: 20 vidéos/mois. Actuellement à 10/mois. Blocage = temps VP pour filmer. Adrian écrit les scripts, filme et édite. VP filme avec lui.',
    avatar_color: '#8b5cf6',
    avatar_initials: 'AC',
    sort_order: 24
  };
  const r1 = await req('POST', 'people', adrian);
  console.log('Adrian added:', r1.status, r1.body || 'OK');

  // Add Adrian tasks/outcomes
  const tasks = {
    person_id: 'c1',
    tasks: [
      {id:'tk_c1a', text:'Livrer 10 vidéos complètes par mois (scripts + filming + editing)', done: false},
      {id:'tk_c1b', text:'Planifier les sessions de filmage avec le VP à l\'avance', done: false},
      {id:'tk_c1c', text:'Soumettre plan de contenu mensuel à Alex pour approbation', done: false}
    ],
    outcomes: [
      {id:'o_c1a', text:'Écrit, filme et édite 10 vidéos/mois pour XGuard'},
      {id:'o_c1b', text:'Coordonne les sessions de filmage avec le VP'},
      {id:'o_c1c', text:'Reporte à Alex (Marketing)'}
    ],
    expected_outcomes: [
      {id:'e_c1a', text:'Objectif: 20 vidéos/mois — doubler la production actuelle'},
      {id:'e_c1b', text:'Plan de contenu soumis à Alex chaque début de mois'},
      {id:'e_c1c', text:'Sessions de filmage planifiées 2 semaines à l\'avance pour libérer le temps VP'}
    ]
  };
  const r2 = await req('POST', 'tasks', tasks);
  console.log('Adrian tasks added:', r2.status, r2.body || 'OK');

  // Update Mitchell notes with 100$ rule
  const mitchellNotes = 'Seul employé présent physiquement au bureau MTL lun-ven 8h-16h30. RÈGLE APPROUVÉE: autorité d\'achat jusqu\'à 100$ sans approbation VP. Au-dessus de 100$ → vient voir le VP. Salaire: 52k → 57k (+5k assumé par VP). Titre à décider (conversation à avoir).';
  const r3 = await req('PATCH', 'people?id=eq.L2', { notes: mitchellNotes });
  console.log('Mitchell notes updated:', r3.status, r3.body || 'OK');

  // Update VP notes
  const vpNotes = `GARDE: Vision stratégique, nouvelles formations (idées + décision finale), filmage vidéos, meetings clés (4-7h/semaine), approbations +100$.

EN TRANSFERT: Gestion trainers → Jessica, décisions opérationnelles courantes → Jessica/Mitchell, achats -100$ → Mitchell autonome, remboursements ÉLITE → Jessica, leads anglais → Mitchell.

OBJECTIF: Libérer temps pour filmer 20 vidéos/mois (actuellement ~10). Brain dump quotidien en cours pour mapper la délégation réelle semaine par semaine.`;
  const r4 = await req('PATCH', 'people?id=eq.vp', { notes: vpNotes });
  console.log('VP notes updated:', r4.status, r4.body || 'OK');
}
run().catch(console.error);
