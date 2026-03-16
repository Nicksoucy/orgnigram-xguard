const SUPABASE_URL = 'https://ctjsdpfegpsfpwjgusyi.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo';

const rows = [
  {
    person_id: 'vp',
    tasks: [
      { id: 't_vp1', text: 'Conversation avec Jessica — formaliser ownership communication & planification trainers', done: false },
      { id: 't_vp2', text: 'Conversation avec Mitchell — reconnaître rôle, annoncer bonification 5k, décider du titre', done: false },
      { id: 't_vp3', text: 'Conversation avec Hamza — présenter outcomes formalisés Lilia & Sekou', done: false },
      { id: 't_vp4', text: 'Conversation structurée avec Dom — divisions Drone + Élite, seuils, objectifs, compensation', done: false },
      { id: 't_vp5', text: 'Conversation avec Marc Éric — trainer-ambassadeur + décider compensation pour références', done: false },
      { id: 't_vp6', text: 'Conversation avec Patrick — formaliser rôle Responsable Québec + rapport mensuel', done: false },
      { id: 't_vp7', text: 'Conversation avec Arnaud — présenter rôle amélioration continue', done: false },
      { id: 't_vp8', text: 'Conversation avec Noureddine — objectif Secourisme Québec, deadline certification', done: false },
      { id: 't_vp9', text: 'Conversation avec Marie-Claude — explorer quel rôle de coordination lui conviendrait', done: false },
      { id: 't_vp10', text: 'URGENT: Décider à qui Heidys reporte (Jessica ou Mitchell) + briefer ce responsable', done: false },
      { id: 't_vp11', text: 'Aligner avec Alex sur priorités Hatem: (1) tracking ventes, (2) rapport inscriptions automatisé', done: false },
      { id: 't_vp12', text: 'Demander à Hatem — créer système de tracking simple pour références Marc Éric', done: false },
    ],
    outcomes: [
      { id: 'o_vp1', text: 'Formation division tourne sans intervention quotidienne du VP' },
      { id: 'o_vp2', text: 'Tous les trainers reportent à Jessica — jamais directement au VP' },
      { id: 'o_vp3', text: 'Équipe SAC reporte exclusivement à Hamza — jamais au VP' },
      { id: 'o_vp4', text: 'Hatem reporte à Alex — le VP ne contacte jamais Hatem directement' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 'L1',
    tasks: [
      { id: 't_l1a', text: 'Émettre les certificats du dernier cours', done: false },
      { id: 't_l1b', text: 'Mettre à jour le calendrier sur le portail et le site', done: false },
      { id: 't_l1c', text: 'Envoyer rappels de disponibilité aux trainers (4 mois à l\'avance)', done: false },
      { id: 't_l1d', text: 'Coordonner avec Dom (Drone + Élite), Patrick (Québec), Mitchell (logistique Montréal)', done: false },
    ],
    outcomes: [
      { id: 'o_l1a', text: 'Gestion de toutes les inscriptions et paiements' },
      { id: 'o_l1b', text: 'Émission des certificats' },
      { id: 'o_l1c', text: 'Rapport d\'inscriptions mensuel livré' },
      { id: 'o_l1d', text: 'Suivi des présences de tous les cours' },
      { id: 'o_l1e', text: 'Affichage de toutes les dates de formation sur le site' },
      { id: 'o_l1f', text: 'Répond à ~95% des courriels entrants' },
      { id: 'o_l1g', text: 'Point de contact principal pour tous les étudiants côté admin' },
      { id: 'o_l1h', text: 'Gestion des bugs du site et portail — signale directement à Hatem (Alex en cc)' },
    ],
    expected_outcomes: [
      { id: 'e_l1a', text: 'Communication & suivi des trainers — ownership complet (point de contact unique pour tous les trainers: absences, disponibilités, confirmations)' },
      { id: 'e_l1b', text: 'Tous les trainers communiquent leur disponibilité 3-4 mois à l\'avance à Jessica' },
      { id: 'e_l1c', text: 'Gestion des remplacements de dernière minute — elle trouve le remplaçant, pas le VP' },
      { id: 'e_l1d', text: 'Planification des horaires — ownership complet (tous les programmes planifiés 3-4 mois à l\'avance)' },
      { id: 'e_l1e', text: 'Calendrier mis à jour en temps réel sur le portail et le site' },
      { id: 'e_l1f', text: 'VP n\'intervient jamais dans la logistique opérationnelle des trainers' },
    ],
  },
  {
    person_id: 'L2',
    tasks: [
      { id: 't_l2a', text: 'Rapport mensuel des commissions envoyé à Jessica pour validation', done: false },
      { id: 't_l2b', text: 'Rapport mensuel opérationnel: état bureau, incidents, besoins identifiés', done: false },
    ],
    outcomes: [
      { id: 'o_l2a', text: 'Réceptionne les clients au bureau — 100% ownership' },
      { id: 'o_l2b', text: 'Ventes sur place — 100% ownership' },
      { id: 'o_l2c', text: 'Traitement de toutes les nouvelles inscriptions et paiements' },
      { id: 'o_l2d', text: 'Gestion des remboursements, plaintes et changements de date' },
      { id: 'o_l2e', text: 'Traitement des documents pour demandes de permis BSP' },
      { id: 'o_l2f', text: 'Gestion complète inventaire uniformes Sécurité XGuard + envois hors région' },
      { id: 'o_l2g', text: 'Gestion calendrier CV + remplacements CV' },
      { id: 'o_l2h', text: 'Cours CV (contractor)' },
    ],
    expected_outcomes: [
      { id: 'e_l2a', text: 'Bureau propre et présentable en tout temps — checklist structurée (quotidien/hebdo/mensuel) maintenue' },
      { id: 'e_l2b', text: 'Après chaque cours: salle remise en ordre selon checklist définie' },
      { id: 'e_l2c', text: 'Tout problème logistique géré par lui — jamais escaladé au VP' },
      { id: 'e_l2d', text: 'Suivi des commissions tenu à jour en temps réel' },
      { id: 'e_l2e', text: 'Rapport mensuel opérationnel livré chaque fin de mois' },
    ],
  },
  {
    person_id: 'L3',
    tasks: [
      { id: 't_l3a', text: 'Implanter nouveaux outcomes Lilia & Sekou (no-shows + boîte courriel)', done: false },
      { id: 't_l3b', text: 'Recadrer Sekou sur la structure de reporting — plus de contact direct au VP', done: false },
      { id: 't_l3c', text: 'Développer scripts de réponse standardisés pour toute l\'équipe SAC', done: false },
    ],
    outcomes: [
      { id: 'o_l3a', text: 'Lilia et Sekou reportent exclusivement à lui — jamais au VP' },
      { id: 'o_l3b', text: 'Supervise qualité des réponses aux commentaires réseaux sociaux (SAC en ligne)' },
      { id: 'o_l3c', text: 'Gère toutes les plaintes étudiantes complexes — zéro escalade au VP' },
      { id: 'o_l3d', text: 'Rapport hebdomadaire SAC au VP — chaque lundi matin (tickets, plaintes, no-shows, courriels, commentaires, points à améliorer)' },
    ],
    expected_outcomes: [
      { id: 'e_l3a', text: 'Équipe SAC opère complètement indépendamment du VP' },
      { id: 'e_l3b', text: 'Si nouveau agent SAC recruté — onboarding complet géré par lui, zéro implication VP' },
      { id: 'e_l3c', text: 'Monitore qualité du service de son équipe en continu' },
      { id: 'e_l3d', text: 'Zéro membre de l\'équipe SAC ne contacte le VP directement' },
    ],
  },
  {
    person_id: 'm1',
    tasks: [
      { id: 't_m1a', text: 'Aligner avec VP sur priorités Hatem: (1) tracking ventes, (2) rapport inscriptions automatisé', done: false },
      { id: 't_m1b', text: 'Planifier calendrier de campagnes 4 semaines à l\'avance', done: false },
    ],
    outcomes: [
      { id: 'o_m1a', text: 'Rapport mensuel marketing avec leads & conversion data' },
      { id: 'o_m1b', text: 'Calendrier de campagnes planifié 4 semaines à l\'avance' },
      { id: 'o_m1c', text: 'Reçoit les rapports de Hatem et fait le suivi avec lui' },
      { id: 'o_m1d', text: 'Discussions stratégiques avec le VP — exécute ensuite avec Hatem' },
    ],
    expected_outcomes: [
      { id: 'e_m1a', text: 'Hatem est entièrement géré par Alex — VP ne contacte jamais Hatem directement' },
      { id: 'e_m1b', text: 'Système de tracking ventes opérationnel pour Marc Éric et Heidys' },
    ],
  },
  {
    person_id: 'm2',
    tasks: [
      { id: 't_m2a', text: 'Créer système de tracking simple pour références Marc Éric et Heidys', done: false },
      { id: 't_m2b', text: 'Automatiser rapport mensuel inscriptions — livré automatiquement à Jessica', done: false },
    ],
    outcomes: [
      { id: 'o_m2a', text: 'Site web maintenu à jour en tout temps' },
      { id: 'o_m2b', text: 'Toutes les automatisations GHL maintenues et fonctionnelles' },
      { id: 'o_m2c', text: 'Portail étudiants maintenu et amélioré en continu' },
    ],
    expected_outcomes: [
      { id: 'e_m2a', text: 'Tout bug ou panne résolu dans les 24h suivant le signalement de Jessica' },
      { id: 'e_m2b', text: 'Système de tracking des ventes opérationnel (priorité)' },
      { id: 'e_m2c', text: 'Rapport mensuel inscriptions automatisé livré à Jessica' },
    ],
  },
  {
    person_id: 't1',
    tasks: [],
    outcomes: [
      { id: 'o_t1a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t1b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t1c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 't2',
    tasks: [],
    outcomes: [
      { id: 'o_t2a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t2b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t2c', text: 'Amélioration continue des formations — les jours sans cours, analyse contenu BSP et identifie améliorations' },
      { id: 'o_t2d', text: 'Standardise et améliore la façon dont les rapports de cours sont faits par les autres trainers' },
    ],
    expected_outcomes: [
      { id: 'e_t2a', text: 'Au moins 1 proposition concrète d\'amélioration par mois à Jessica ou au VP (format: quoi changer, pourquoi, comment)' },
      { id: 'e_t2b', text: 'Les jours sans cours = temps d\'analyse et propositions, pas du temps libre' },
    ],
  },
  {
    person_id: 't3',
    tasks: [],
    outcomes: [
      { id: 'o_t3a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t3b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t3c', text: 'À chaque cours: présenter activement le Programme Élite aux étudiants BSP éligibles' },
      { id: 'o_t3d', text: 'Mentionner systématiquement les formations complémentaires (Gestion de crise, Secourisme, etc.)' },
      { id: 'o_t3e', text: 'Rapport mensuel simple: références et ventes générées — envoyé à Jessica' },
    ],
    expected_outcomes: [
      { id: 'e_t3a', text: 'Référer les ventes d\'équipement via lien ou code trackable créé par Hatem' },
      { id: 'e_t3b', text: 'Aucune coordination de trainers / Aucune tâche administrative / Aucun suivi d\'inscriptions' },
    ],
  },
  {
    person_id: 't4',
    tasks: [],
    outcomes: [
      { id: 'o_t4a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t4b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t4c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 't5',
    tasks: [],
    outcomes: [],
    expected_outcomes: [
      { id: 'e_t5a', text: '\u26d4 INACTIVE — aucune tâche ni cours à assigner. À garder en contact pour éventuel retour.' },
    ],
  },
  {
    person_id: 't7',
    tasks: [],
    outcomes: [
      { id: 'o_t7a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t7b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t7c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [
      { id: 'e_t7a', text: 'Absences à monitorer — si pattern se répète, conversation via Jessica' },
    ],
  },
  {
    person_id: 't8',
    tasks: [],
    outcomes: [
      { id: 'o_t8a', text: '1 session BSP par mois à Québec (soir)' },
      { id: 'o_t8b', text: 'Coordination des autres professeurs à Québec' },
      { id: 'o_t8c', text: 'Gestion de la salle et de la logistique sur place' },
      { id: 'o_t8d', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t8e', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
    ],
    expected_outcomes: [
      { id: 'e_t8a', text: 'Rapport mensuel opérationnel Québec — envoyé au VP chaque dernier vendredi du mois (tâches, état salle, trainers Québec, points à améliorer)' },
      { id: 'e_t8b', text: 'Gestion générale des opérations de l\'académie à Québec — ownership complet' },
    ],
  },
  {
    person_id: 't9',
    tasks: [],
    outcomes: [
      { id: 'o_t9a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t9b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t9c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 't10',
    tasks: [],
    outcomes: [
      { id: 'o_t10a', text: '1 cours BSP en ligne par mois, le soir' },
      { id: 'o_t10b', text: 'Backup pour les cours de jour en présentiel à Montréal' },
      { id: 'o_t10c', text: 'Disponibilité pour remplacements confirmée rapidement quand Jessica le contacte' },
      { id: 'o_t10d', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t10e', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 't11',
    tasks: [],
    outcomes: [
      { id: 'o_t11a', text: 'Division Drone — ownership complet: ventes, classes, annulations, rescédulations' },
      { id: 'o_t11b', text: 'Planifie toutes les dates de classes Drone avec Jessica — elle affiche sur le site' },
      { id: 'o_t11c', text: 'Gère le seuil minimum d\'inscriptions par classe — annule et rescédule si non atteint' },
      { id: 'o_t11d', text: 'Division Élite — ownership complet de la croissance et pérennité du programme (99$/mois)' },
      { id: 'o_t11e', text: 'Responsable de faire grossir le nombre d\'abonnés actifs Élite' },
      { id: 'o_t11f', text: 'Formation BSP en ligne en continu — soirs Lun-Jeu + week-end' },
      { id: 'o_t11g', text: 'Rapport mensuel au VP: classes livrées, inscriptions, annulations, revenus générés (Drone + Élite)' },
    ],
    expected_outcomes: [
      { id: 'e_t11a', text: 'Zéro décision opérationnelle Drone qui remonte au VP' },
      { id: 'e_t11b', text: 'Rapport mensuel livré proactivement — format exact à être montré une fois par le VP' },
      { id: 'e_t11c', text: 'Seuil minimum d\'inscriptions + objectif ventes mensuel Drone + Élite à définir avec VP' },
    ],
  },
  {
    person_id: 't12',
    tasks: [
      { id: 't_t12a', text: 'S\'inscrire lui-même à la certification Secourisme — deadline à fixer', done: false },
    ],
    outcomes: [
      { id: 'o_t12a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t12b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t12c', text: 'Formation BSP à Québec — ~1.5 formation/mois' },
    ],
    expected_outcomes: [
      { id: 'e_t12a', text: 'Devenir formateur en Secourisme en milieu de travail à Québec (objectif de développement)' },
      { id: 'e_t12b', text: 'Revenir avec un plan de match sans que le VP ait à relancer' },
      { id: 'e_t12c', text: 'Une fois certifié: gérer son propre calendrier Secourisme à Québec' },
    ],
  },
  {
    person_id: 't13',
    tasks: [],
    outcomes: [
      { id: 'o_t13a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t13b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t13c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [],
  },
  {
    person_id: 't14',
    tasks: [],
    outcomes: [
      { id: 'o_t14a', text: 'Rapport de présence envoyé à Jessica après chaque cours' },
      { id: 'o_t14b', text: 'Disponibilité communiquée 3-4 mois à l\'avance à Jessica' },
      { id: 'o_t14c', text: 'Tout imprévu ou absence signalé à Jessica directement — jamais au VP' },
    ],
    expected_outcomes: [
      { id: 'e_t14a', text: 'Explorer quel rôle de coordination lui conviendrait (pistes: trainers RCR Montréal, remplacements, backup)' },
      { id: 'e_t14b', text: 'Potentiel: onboarding nouveaux trainers si rôle de coordination confirmé' },
    ],
  },
  {
    person_id: 's2',
    tasks: [],
    outcomes: [
      { id: 'o_s2a', text: 'Toutes les demandes étudiantes des soirs de semaine traitées dans les 24h' },
      { id: 'o_s2b', text: 'Escalade vers Hamza uniquement — jamais vers le VP, sans exception' },
      { id: 'o_s2c', text: 'Résumé des tickets envoyé à Hamza chaque vendredi soir' },
      { id: 'o_s2d', text: 'No-shows Secourisme en semaine — ownership complet: appel immédiat à tous les absents, objectif recéduler avec frais 50$' },
      { id: 'o_s2e', text: 'Boîte courriel formations — gère les soirs de semaine, répond aux questions standards, escalade à Hamza si dépassé' },
    ],
    expected_outcomes: [
      { id: 'e_s2a', text: 'Suivi des no-shows et résultats envoyé à Hamza chaque vendredi soir' },
      { id: 'e_s2b', text: 'Zéro contact direct avec le VP — tout passe par Hamza' },
    ],
  },
  {
    person_id: 's3',
    tasks: [],
    outcomes: [
      { id: 'o_s3a', text: 'Toutes les demandes étudiantes du week-end traitées dans les 24h' },
      { id: 'o_s3b', text: 'Escalade vers Hamza uniquement — jamais vers le VP, sans exception' },
      { id: 'o_s3c', text: 'Résumé des tickets week-end envoyé à Hamza chaque dimanche soir' },
      { id: 'o_s3d', text: 'No-shows Secourisme le week-end — ownership complet: appel immédiat à tous les absents, objectif recéduler avec frais 50$' },
      { id: 'o_s3e', text: 'Boîte courriel formations — gère le week-end, répond aux questions standards, escalade à Hamza si dépassé' },
    ],
    expected_outcomes: [
      { id: 'e_s3a', text: 'Suivi des no-shows et résultats envoyé à Hamza chaque dimanche soir' },
      { id: 'e_s3b', text: '\u26a0 À recadrer: ne plus contacter le VP directement — tout passe par Hamza' },
    ],
  },
  {
    person_id: 'v1',
    tasks: [
      { id: 't_v1a', text: 'Décider du responsable de Heidys (Jessica ou Mitchell) — URGENT', done: false },
      { id: 't_v1b', text: 'Laisser tourner 2-3 semaines pour établir baseline avant de fixer des targets', done: false },
    ],
    outcomes: [
      { id: 'o_v1a', text: 'Appels sortants (cold/warm leads) — 20h/semaine' },
    ],
    expected_outcomes: [
      { id: 'e_v1a', text: 'Rapport hebdomadaire obligatoire envoyé à son responsable chaque vendredi: appels effectués, ventes conclues, heures travaillées, suivis, 2e calls, overview semaine' },
      { id: 'e_v1b', text: 'Targets à définir après évaluation baseline: appels sortants minimum/semaine, leads contactés minimum, taux de conversion cible' },
      { id: 'e_v1c', text: 'Reporte à Jessica ou Mitchell — plus jamais directement au VP' },
    ],
  },
];

async function seed() {
  console.log(`Seeding ${rows.length} task rows into Supabase...\n`);

  const res = await fetch(`${SUPABASE_URL}/rest/v1/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
      'Prefer': 'resolution=merge-duplicates',
    },
    body: JSON.stringify(rows),
  });

  const text = await res.text();
  console.log(`Status: ${res.status} ${res.statusText}`);
  if (text) {
    console.log('Response:', text);
  }

  if (res.ok) {
    console.log(`\nDone — ${rows.length} rows upserted successfully.`);
  } else {
    console.error('\nFailed to seed tasks.');
    process.exit(1);
  }
}

seed();
