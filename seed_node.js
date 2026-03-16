const https = require('https');
const SUPABASE_URL = 'https://ctjsdpfegpsfpwjgusyi.supabase.co';
const KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

function post(table, rows) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(rows);
    const req = https.request({
      hostname: 'ctjsdpfegpsfpwjgusyi.supabase.co',
      path: '/rest/v1/' + table,
      method: 'POST',
      headers: {
        'apikey': KEY,
        'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          console.error(table + ' ERROR ' + res.statusCode + ': ' + d);
        } else {
          console.log(table + ': OK (' + res.statusCode + ')');
        }
        resolve();
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

const people = [
  {id:'vp',name:'You',role:'VP of Training',type:'exec',dept:'all',reports_to:null,programs:[],schedule:'',delegate:'no',notes:'',avatar_color:'#ff6b35',avatar_initials:'YO',sort_order:0},
  {id:'L1',name:'Jessica Clermont',role:'Coordonnatrice à la formation',type:'lead',dept:'training',reports_to:'vp',programs:['BSP','RCR','Élite','CV','Drone'],schedule:'Lun-Ven, jour',delegate:'partial',notes:'Pilier central de l académie. Très fiable, très organisée, proactive.',avatar_color:'#34d399',avatar_initials:'JC',sort_order:10},
  {id:'L2',name:'Mitchell Skelton',role:'Technicien service à la clientèle',type:'lead',dept:'training',reports_to:'vp',programs:['CV'],schedule:'Lun-Ven 8h-16h30',delegate:'partial',notes:'Seul employé physiquement présent au bureau Montréal. Salaire 52 000$ -> 57 000$.',avatar_color:'#60a5fa',avatar_initials:'MS',sort_order:11},
  {id:'L3',name:'Hamza Maghraoui',role:'Responsable contractuel du service à la clientèle',type:'lead',dept:'sac',reports_to:'vp',programs:['SAC'],schedule:'Remote — facturation hebdomadaire',delegate:'yes',notes:'En poste depuis 5 jan 2026. Contractor: 23$/h. NDA signé.',avatar_color:'#a78bfa',avatar_initials:'HM',sort_order:12},
  {id:'t1',name:'Jean Bonnet Lundy',role:'Trainer BSP',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Soir + week-end (flexible)',delegate:'no',notes:'Très fiable, toujours présent. Trainer stable.',avatar_color:'#fbbf24',avatar_initials:'JB',sort_order:20},
  {id:'t2',name:'Arnaud Deffert',role:'Trainer BSP + Responsable amélioration continue',type:'employee',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Jour',delegate:'yes',notes:'EMPLOYÉ. Très fiable. Ressource sous-utilisée.',avatar_color:'#f472b6',avatar_initials:'AD',sort_order:21},
  {id:'t3',name:'Marc Éric Deschambault',role:'Trainer BSP/RCR/Élite/Gestion de crise/Secourisme — Trainer-ambassadeur',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP','RCR','Élite','Gestion de crise','Secourisme'],schedule:'BSP soir (1 sur 2) / Secourisme 1-2x semaine',delegate:'yes',notes:'Très polyvalent. Vendeur naturel. PAS fiable sur tâches admin.',avatar_color:'#22d3ee',avatar_initials:'MD',sort_order:22},
  {id:'t4',name:'Khaled Deramoune',role:'Trainer RCR / Secourisme',type:'contractor',dept:'training',reports_to:'vp',programs:['RCR'],schedule:'Jour — 2 formations/semaine',delegate:'no',notes:'Très fiable. Pas ambition de croissance.',avatar_color:'#f87171',avatar_initials:'KD',sort_order:23},
  {id:'t5',name:'Monia Baraka',role:'Trainer RCR / Secourisme — INACTIVE',type:'contractor',dept:'training',reports_to:'vp',programs:['RCR','Secourisme'],schedule:'N/A — INACTIVE',delegate:'no',notes:'NON ACTIVE — a communiqué son intention de se retirer.',avatar_color:'#86efac',avatar_initials:'MB',sort_order:24},
  {id:'t7',name:'Mélina Bédard',role:'Trainer RCR / Secourisme',type:'contractor',dept:'training',reports_to:'vp',programs:['RCR'],schedule:'Jour — quelques cours/mois',delegate:'no',notes:'Généralement fiable avec quelques absences occasionnelles.',avatar_color:'#fdba74',avatar_initials:'MB',sort_order:25},
  {id:'t8',name:'Patrick Bourque',role:'Trainer BSP + Responsable opérations Québec',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Soir — 1 session BSP/mois',delegate:'yes',notes:'Pilier physique de Québec, équivalent de Mitchell à Montréal.',avatar_color:'#ff6b35',avatar_initials:'PB',sort_order:26},
  {id:'t9',name:'Mohamed Maghraoui',role:'Trainer BSP',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Week-end — en continu',delegate:'no',notes:'Trainer stable. Donne BSP en ligne chaque week-end.',avatar_color:'#34d399',avatar_initials:'MM',sort_order:27},
  {id:'t10',name:'Bertrand Lauture',role:'Trainer BSP — Backup jour Montréal',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Jour + Soir, flexible',delegate:'no',notes:'Backup de jour, disponible pour remplacements.',avatar_color:'#60a5fa',avatar_initials:'BL',sort_order:28},
  {id:'t11',name:'Domingos Oliveira',role:'Trainer BSP + Responsable Division Drone + Élite',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP','Élite','Drone'],schedule:'Lun-Jeu 9h-16h + soirs + week-end (JAMAIS vendredi)',delegate:'yes',notes:'Très fiable, pratiquement temps plein contractor.',avatar_color:'#a78bfa',avatar_initials:'DO',sort_order:29},
  {id:'t12',name:'Noureddine Fatnassy',role:'Trainer BSP — Objectif: Secourisme Québec',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Jour — ~1.5 formation BSP/mois',delegate:'no',notes:'Très fiable. Objectif: formateur Secourisme à Québec.',avatar_color:'#fbbf24',avatar_initials:'NF',sort_order:30},
  {id:'t13',name:'Romann Chapelain',role:'Trainer BSP',type:'contractor',dept:'training',reports_to:'vp',programs:['BSP'],schedule:'Soir — 1 session BSP/mois',delegate:'no',notes:'Trainer stable. 1 session par mois.',avatar_color:'#f472b6',avatar_initials:'RC',sort_order:31},
  {id:'t14',name:'Marie-Claude Gosselin',role:'Trainer RCR/BSP — Potentiel rôle coordination',type:'contractor',dept:'training',reports_to:'vp',programs:['RCR','BSP'],schedule:'Jour + Week-end — 4 à 6 cours/mois',delegate:'yes',notes:'A exprimé intérêt pour rôle de coordination.',avatar_color:'#22d3ee',avatar_initials:'MG',sort_order:32},
  {id:'s2',name:'Lilia Hassen',role:'Service à la clientèle — Soir semaine',type:'contractor',dept:'sac',reports_to:'L3',programs:['SAC'],schedule:'Lun-Ven, soir',delegate:'no',notes:'Très fiable. Reporte à Hamza uniquement.',avatar_color:'#f87171',avatar_initials:'LH',sort_order:40},
  {id:'s3',name:'Sekou Isaint',role:'Service à la clientèle — Week-end',type:'contractor',dept:'sac',reports_to:'L3',programs:['SAC'],schedule:'Sam-Dim',delegate:'no',notes:'Très fiable. Contacte VP directement à recadrer.',avatar_color:'#86efac',avatar_initials:'SI',sort_order:41},
  {id:'m1',name:'Alexandre Butterfield',role:'Directeur Marketing / Co-fondateur Dark Horse Ads',type:'lead',dept:'marketing',reports_to:'vp',programs:['MKT'],schedule:'Always on',delegate:'no',notes:'Maxed out — ne pas surcharger.',avatar_color:'#fdba74',avatar_initials:'AB',sort_order:50},
  {id:'m2',name:'Hatem Dhaouadi',role:'Automation & Web Builder',type:'contractor',dept:'marketing',reports_to:'m1',programs:['MKT'],schedule:'When needed',delegate:'no',notes:'Reporte à Alex. Compétences: automatisation, dev web, GHL.',avatar_color:'#ff6b35',avatar_initials:'HD',sort_order:51},
  {id:'v1',name:'Heidys Garcia',role:'Vendeuse',type:'contractor',dept:'sales',reports_to:'vp',programs:['Sales'],schedule:'20h/semaine',delegate:'no',notes:'URGENT: Pas de targets définis. Appels sortants cold/warm leads.',avatar_color:'#34d399',avatar_initials:'HG',sort_order:60}
];

// Convert delegate text -> bool for DB (yes/partial=true, no=false)
people.forEach(p => { p.delegate = (p.delegate === 'yes' || p.delegate === 'partial'); });

post('people', people).then(() => {
  console.log('All people seeded!');
  process.exit(0);
}).catch(e => {
  console.error(e);
  process.exit(1);
});
