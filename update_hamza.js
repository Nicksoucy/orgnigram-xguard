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
  // Update Hamza notes
  const personUpdate = {
    notes: 'Responsable SAC — gère Lilia (soir semaine) et Sekou (week-end). Utilise JustCall pour tous les appels (connecté à GHL) — stats disponibles automatiquement. A produit le SOP XGuard V2 (21 pages) et rapport hebdo structuré. Rapport hebdo soumis chaque vendredi directement dans l\'app.'
  };
  const r1 = await req('PATCH', 'people?id=eq.L3', personUpdate);
  console.log('Update person:', r1.status, r1.body || 'OK');

  // Update tasks/outcomes
  const tasksUpdate = {
    tasks: [
      { id: 'tk_L3a', text: 'Soumettre rapport KPI hebdo chaque vendredi dans l\'app (volume appels JustCall, inscriptions, plaintes, escalades, observations, besoins)', done: false },
      { id: 'tk_L3b', text: 'Adresser le problème systémique des plaintes prélèvement ÉLITE (3-5/jour) — escalader au VP avec proposition de solution', done: false },
      { id: 'tk_L3c', text: 'Connecter les leads "recrutement post-formation" (3-4/jour) avec Banji — créer protocole de transfert', done: false },
      { id: 'tk_L3d', text: 'Briefer Lilia et Sekou sur le SOP V2 — s\'assurer que les scripts et protocoles sont appliqués', done: false }
    ],
    outcomes: [
      { id: 'o_L3a', text: 'Gère toute l\'équipe SAC: Lilia (soir semaine) et Sekou (week-end)' },
      { id: 'o_L3b', text: 'Supervise tous les appels entrants et sortants via JustCall (connecté GHL)' },
      { id: 'o_L3c', text: 'A créé et maintient le SOP XGuard V2 — guide officiel pour toute l\'équipe SAC' },
      { id: 'o_L3d', text: 'Gère les escalades: étudiant frustré (-30 min), commentaire négatif viral (immédiat)' },
      { id: 'o_L3e', text: 'Produit rapport hebdo: volume appels par agent, inscriptions conclues, plaintes, tendances' }
    ],
    expected_outcomes: [
      { id: 'e_L3a', text: 'KPI hebdo chaque vendredi: appels entrants/sortants par agent (Lilia/Sekou/Hamza), inscriptions conclues par formation, plaintes reçues + % résolues en -30 min, escalades au VP (objectif: 0), observations + besoins semaine' },
      { id: 'e_L3b', text: 'Taux de réponse aux appels entrants: objectif à définir (baseline JustCall)' },
      { id: 'e_L3c', text: 'Zéro escalade au VP pour situations gérables par SAC (protocole SOP respecté)' },
      { id: 'e_L3d', text: 'SOP V2 appliqué par toute l\'équipe — scripts ARCA utilisés systématiquement' }
    ]
  };
  const r2 = await req('PATCH', 'tasks?person_id=eq.L3', tasksUpdate);
  console.log('Update tasks:', r2.status, r2.body || 'OK');
}

run().catch(console.error);
