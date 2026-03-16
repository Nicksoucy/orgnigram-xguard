const SUPABASE_URL='https://ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';
const h={'apikey':KEY,'Authorization':'Bearer '+KEY,'Content-Type':'application/json'};

const row = {
  person_id: 'v1',
  tasks: [
    {id:'t_v1a', text:"Décider du responsable de Heidys (Jessica ou Mitchell) — URGENT", done:false},
    {id:'t_v1b', text:"Laisser tourner 2-3 semaines pour établir baseline avant de fixer des targets", done:false}
  ],
  outcomes: [
    {id:'o_v1a', text:"Appels sortants (cold/warm leads) — 20h/semaine"}
  ],
  expected_outcomes: [
    {id:'e_v1a', text:"Rapport hebdomadaire obligatoire envoyé à son responsable chaque vendredi: appels effectués, ventes conclues, heures travaillées, suivis, 2e calls, overview semaine"},
    {id:'e_v1b', text:"Targets à définir après évaluation baseline: appels sortants minimum/semaine, leads contactés minimum, taux de conversion cible"},
    {id:'e_v1c', text:"Reporte à Jessica ou Mitchell — plus jamais directement au VP"}
  ]
};

fetch(SUPABASE_URL+'/rest/v1/tasks', {
  method:'POST',
  headers:{...h,'Prefer':'return=minimal'},
  body: JSON.stringify(row)
}).then(r => {
  console.log('Status:', r.status);
  return r.text();
}).then(t => console.log(t||'OK')).catch(console.error);
