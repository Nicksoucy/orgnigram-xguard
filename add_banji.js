const https = require('https');
const SUPABASE_HOST = 'ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function req(method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: SUPABASE_HOST,
      path: '/rest/v1/' + path,
      method,
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
    if (data) r.write(data);
    r.end();
  });
}

async function run() {
  const person = {
    id: 'r1', name: 'Banji',
    role: 'Responsable recrutement — Entrevues agents & premiers appels Élite',
    dept: 'recrutement', type: 'contractor', reports_to: 'vp',
    programs: [], schedule: '16h–40h/semaine selon besoin',
    delegate: false,
    notes: 'Contact direct avec les profs pour top 1-5 par cohorte. Demandes marketing à Alex (VP en CC). Gère tous les premiers appels Élite.',
    avatar_color: '#f97316', avatar_initials: 'BA', sort_order: 23
  };
  const r1 = await req('POST', 'people', person);
  console.log('Person:', r1.status, r1.body || 'OK');

  const tasks = {
    person_id: 'r1',
    tasks: [
      {id:'tk_r1a', text:'Contacter chaque prof dans les 48h suivant la fin de chaque cohorte BSP pour obtenir le top 1–5 (évaluation du prof)', done: false},
      {id:'tk_r1b', text:'Envoyer demandes marketing structurées à Alex (VP en CC) — région, poste, certifications requises, disponibilités', done: false},
      {id:'tk_r1c', text:'Synchroniser avec Jessica pour accès au calendrier des fins de formation gardiennage', done: false},
      {id:'tk_r1d', text:'Soumettre rapport KPI chaque vendredi', done: false}
    ],
    outcomes: [
      {id:'o_r1a', text:'Conduit toutes les entrevues initiales des agents de sécurité pour XGuard'},
      {id:'o_r1b', text:'Gère tous les premiers appels Élite'},
      {id:'o_r1c', text:'Contacte directement les profs à la fin de chaque cohorte — obtient top 1–5 par évaluation du prof'},
      {id:'o_r1d', text:'Soumet demandes recrutement ciblées à Alex Marketing (VP en CC) — format: poste, région, certifications, disponibilités'}
    ],
    expected_outcomes: [
      {id:'e_r1a', text:'100% des cohortes BSP ont un top 5 transmis dans les 48h suivant la fin de formation'},
      {id:'e_r1b', text:'Zéro agent embauché sans avoir passé l\'entrevue Banji en premier'},
      {id:'e_r1c', text:'Toutes les demandes marketing sont structurées et actionnables (région, poste, critères précis)'},
      {id:'e_r1d', text:'KPI hebdo chaque vendredi: entrevues complétées, retenus/refusés, top 5 cohortes reçus, demandes marketing, appels Élite, pipeline actif total'}
    ]
  };
  const r2 = await req('POST', 'tasks', tasks);
  console.log('Tasks:', r2.status, r2.body || 'OK');
}
run().catch(console.error);
