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

const people = [
  {
    id: 'L3',
    tasks: [
      {id:'tk_L3a', text:'Soumettre rapport hebdo SAC chaque lundi matin (volume appels, annulations, observations)', done:false},
      {id:'tk_L3b', text:'Transmettre dossiers remboursements/annulations ÉLITE à Jessica immédiatement', done:false},
      {id:'tk_L3c', text:'Transmettre leads anglais non rappelés à Mitchell avec suivi', done:false},
      {id:'tk_L3d', text:'Implanter nouveaux scripts de réponse SAC (no-shows + boîte courriel)', done:false},
      {id:'tk_L3e', text:'Recadrer Sekou sur structure de reporting — plus de contact direct au VP', done:false}
    ],
    outcomes: [
      {id:'o_L3a', text:"Gère toute l'équipe SAC (Lilia + Sekou) — supervision quotidienne"},
      {id:'o_L3b', text:'Rapport hebdomadaire SAC soumis au VP chaque lundi'},
      {id:'o_L3c', text:'Point de contact unique VP pour tout ce qui concerne le service à la clientèle'},
      {id:'o_L3d', text:'Escalade leads anglais → Mitchell, remboursements ÉLITE → Jessica'}
    ],
    expected_outcomes: [
      {id:'e_L3a', text:'Taux de réponse appels SAC ≥ 85% chaque semaine'},
      {id:'e_L3b', text:'Zéro remboursement ÉLITE en attente plus de 72h'},
      {id:'e_L3c', text:'Rapport hebdo soumis sans relance — chaque lundi avant 10h'},
      {id:'e_L3d', text:'Zéro contact direct Lilia/Sekou → VP — tout passe par Hamza'}
    ]
  },
  {
    id: 'L2',
    tasks: [
      {id:'tk_L2a', text:'Conversation VP à venir: formaliser titre + annoncer bonification 5k', done:false},
      {id:'tk_L2b', text:'Créer checklist remise en ordre salle après chaque cours', done:false},
      {id:'tk_L2c', text:'Coordonner Pascaline (checklist quotidien/hebdo/mensuel)', done:false},
      {id:'tk_L2d', text:'Prendre en charge leads anglais transmis par Hamza — suivi obligatoire', done:false}
    ],
    outcomes: [
      {id:'o_L2a', text:'Seul employé présent physiquement au bureau MTL lun-ven 8h-16h30'},
      {id:'o_L2b', text:'Réception clients (~60-80/jour), inscriptions, paiements, remboursements, changements de date'},
      {id:'o_L2c', text:'Traitement documents permis BSP, dépôt chèques, archivage SharePoint'},
      {id:'o_L2d', text:'Support technique aux profs, impression exercices/examens'},
      {id:'o_L2e', text:'Gestion entretien bâtiment + coordination sous-traitants'},
      {id:'o_L2f', text:'Suivi commissions — compile et soumet au VP pour approbation'},
      {id:'o_L2g', text:'Ventes uniformes/équipements (Talliup et Poynt)'},
      {id:'o_L2h', text:'Prend en charge leads anglais non rappelés transmis par Hamza'}
    ],
    expected_outcomes: [
      {id:'e_L2a', text:'Bureau propre et présentable en tout temps'},
      {id:'e_L2b', text:'Salle remise en ordre après chaque cours (checklist)'},
      {id:'e_L2c', text:'Rapport mensuel opérationnel soumis au VP: état bureau, incidents, besoins'},
      {id:'e_L2d', text:'Suivi commissions à jour en temps réel — soumis au VP pour approbation mensuelle'},
      {id:'e_L2e', text:"100% leads anglais transmis par Hamza contactés dans les 24h"},
      {id:'e_L2f', text:"Problèmes escaladés résolus avant d'arriver au VP — max 1 escalade/mois"}
    ]
  },
  {
    id: 'v1',
    tasks: [
      {id:'tk_v1a', text:'Travailler exclusivement dans GHL + JustCall — zéro appel hors système', done:false},
      {id:'tk_v1b', text:'Soumettre rapport KPI chaque vendredi: appels 1ers, 2e appels, 3e appels+, inscriptions, heures, overview', done:false},
      {id:'tk_v1c', text:'Reporter à Jessica ou Mitchell — plus jamais directement au VP', done:false}
    ],
    outcomes: [
      {id:'o_v1a', text:'Appels sortants sur leads qualifiés (formulaire site) — sources: TikTok, Google, Instagram'},
      {id:'o_v1b', text:'Vend formations gardiennage BSP, Secourisme, Élite (Drone à venir)'},
      {id:'o_v1c', text:'Travaille via JustCall pour les appels + tout logué dans GHL obligatoire'}
    ],
    expected_outcomes: [
      {id:'e_v1a', text:'100% des appels et suivis loggés dans GHL — zéro activité hors système'},
      {id:'e_v1b', text:'Rapport KPI soumis chaque vendredi sans exception'},
      {id:'e_v1c', text:'Reporter à Jessica ou Mitchell — plus jamais directement au VP'},
      {id:'e_v1d', text:'Targets à définir après 3-4 semaines de baseline (appels/semaine, taux conversion, inscriptions)'},
      {id:'e_v1e', text:'Max 20h/semaine facturées — toute heure supplémentaire doit être approuvée'}
    ]
  },
  {
    id: 'r1',
    tasks: [
      {id:'tk_r1a', text:'Contacter chaque prof dans les 48h suivant la fin de chaque cohorte BSP — obtenir top 1-5 par évaluation du prof', done:false},
      {id:'tk_r1b', text:'Envoyer demandes marketing structurées à Alex (VP en CC) — région, poste, certifications requises, disponibilités', done:false},
      {id:'tk_r1c', text:'Synchroniser avec Jessica pour accès au calendrier des fins de formation gardiennage', done:false},
      {id:'tk_r1d', text:'Soumettre rapport KPI chaque vendredi', done:false}
    ],
    outcomes: [
      {id:'o_r1a', text:'Conduit toutes les entrevues initiales des agents de sécurité pour XGuard'},
      {id:'o_r1b', text:'Gère tous les premiers appels Élite'},
      {id:'o_r1c', text:'Contacte directement les profs à la fin de chaque cohorte — obtient top 1-5 par évaluation du prof'},
      {id:'o_r1d', text:'Soumet demandes recrutement ciblées à Alex Marketing (VP en CC) — format: poste, région, certifications, disponibilités'}
    ],
    expected_outcomes: [
      {id:'e_r1a', text:'100% des cohortes BSP ont un top 5 transmis dans les 48h suivant la fin de formation'},
      {id:'e_r1b', text:"Zéro agent embauché sans avoir passé l'entrevue Banji en premier"},
      {id:'e_r1c', text:'Toutes les demandes marketing sont structurées et actionnables (région, poste, critères précis)'},
      {id:'e_r1d', text:'KPI hebdo chaque vendredi: entrevues complétées, retenus/refusés, top 5 cohortes reçus, demandes marketing, appels Élite, pipeline actif total'}
    ]
  }
];

async function updatePerson(p) {
  console.log(`\n=== Updating ${p.id} ===`);

  // PATCH tasks row for this person
  const payload = {
    tasks: p.tasks,
    outcomes: p.outcomes,
    expected_outcomes: p.expected_outcomes
  };

  const r = await req('PATCH', `/rest/v1/tasks?person_id=eq.${p.id}`, payload);
  console.log(`  PATCH /rest/v1/tasks?person_id=eq.${p.id}  → ${r.status}`);
  if (r.body && r.body.length > 0 && r.body !== '[]') console.log(`  body: ${r.body.slice(0,200)}`);

  // If no row existed (204 = ok, but let's also try INSERT if 404 or empty)
  // Check if row exists first
  if (r.status === 404 || r.status === 406) {
    console.log(`  Row not found, attempting INSERT...`);
    const ins = await req('POST', '/rest/v1/tasks', { person_id: p.id, ...payload });
    console.log(`  POST /rest/v1/tasks  → ${ins.status}`);
    if (ins.body) console.log(`  body: ${ins.body.slice(0,200)}`);
  }

  return r.status;
}

async function main() {
  // First check if rows exist for each person
  for (const p of people) {
    const check = await req('GET', `/rest/v1/tasks?person_id=eq.${p.id}&select=person_id`, null);
    console.log(`\nGET tasks for ${p.id} → ${check.status} | body: ${check.body}`);

    if (check.status === 200 && check.body !== '[]' && check.body.includes(p.id)) {
      // Row exists, PATCH
      await updatePerson(p);
    } else {
      // Insert new row
      console.log(`  No existing row for ${p.id}, inserting...`);
      const payload = {
        person_id: p.id,
        tasks: p.tasks,
        outcomes: p.outcomes,
        expected_outcomes: p.expected_outcomes
      };
      const ins = await req('POST', '/rest/v1/tasks', payload);
      console.log(`  POST /rest/v1/tasks (${p.id}) → ${ins.status}`);
      if (ins.body && ins.body.length > 2) console.log(`  body: ${ins.body.slice(0,300)}`);
    }
  }

  console.log('\n=== DONE ===');
}

main().catch(console.error);
