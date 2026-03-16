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
  // Update Mitchell notes
  const personUpdate = {
    notes: '💰 Salaire: 52k → 57k (+5k assumé par VP — demandait 60k). 📋 Titre à décider: Gérant de l\'académie / Gérant de la formation / Responsable de la formation — conversation à avoir. SEUL employé présent physiquement au bureau MTL lun-ven. Scheduling profs → Jessica. Commissions → Mitchell compile, VP approuve. Checklist Pascaline (ménage 2x/sem) à créer et maintenir. Services anglais: seul anglophone naturel de la compagnie.'
  };
  const r1 = await req('PATCH', 'people?id=eq.L2', personUpdate);
  console.log('Update person:', r1.status, r1.body || 'OK');

  // Update tasks/outcomes
  const tasksUpdate = {
    tasks: [
      { id: 'tk_L2a', text: 'Créer checklist Pascaline (quotidien/hebdo/mensuel) et s\'assurer qu\'elle est suivie', done: false },
      { id: 'tk_L2b', text: 'Conversation VP à venir: formaliser titre + annoncer bonification 5k', done: false },
      { id: 'tk_L2c', text: 'Créer checklist remise en ordre salle après chaque cours', done: false },
      { id: 'tk_L2d', text: 'Soumettre rapport KPI mensuel au VP', done: false }
    ],
    outcomes: [
      { id: 'o_L2a', text: 'Seul employé présent physiquement au bureau MTL lun-ven 8h-16h30 — premier répondant pour tout' },
      { id: 'o_L2b', text: 'Accueil clients sur place (~60-80/jour), inscriptions, paiements, remboursements, changements de date' },
      { id: 'o_L2c', text: 'Traitement documents BSP, dépôt chèques, archivage SharePoint' },
      { id: 'o_L2d', text: 'Gestion entretien bâtiment, coordination sous-traitants, coordination Pascaline (ménage 2x/semaine)' },
      { id: 'o_L2e', text: 'Support technique profs, impression examens/exercices' },
      { id: 'o_L2f', text: 'Suivi commissions compilé et soumis au VP pour approbation' },
      { id: 'o_L2g', text: 'Services en anglais — seul anglophone naturel de la compagnie' }
    ],
    expected_outcomes: [
      { id: 'e_L2a', text: 'KPI mensuel: checklist Pascaline suivie ✓/✗, rapport opérationnel (état bureau, incidents, besoins), problèmes escaladés résolus avant d\'arriver au VP (chiffre), salle remise en ordre après chaque cours ✓/✗' },
      { id: 'e_L2b', text: 'Commissions compilées et envoyées au VP chaque mois pour approbation — zéro retard' },
      { id: 'e_L2c', text: '📋 Titre à finaliser lors de la prochaine conversation VP-Mitchell' },
      { id: 'e_L2d', text: 'Scheduling profs → Jessica (pas Mitchell)' }
    ]
  };
  const r2 = await req('PATCH', 'tasks?person_id=eq.L2', tasksUpdate);
  console.log('Update tasks:', r2.status, r2.body || 'OK');
}

run().catch(console.error);
