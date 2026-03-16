-- ============================================================
-- XGuard Org Chart — Supabase Seed Data
-- Generated from index.html on 2026-03-15
-- Safe to re-run: uses ON CONFLICT DO UPDATE for all tables
-- ============================================================

-- ============================================================
-- 1. DEPARTMENTS
-- (Source: departments array + CV_DIVS are dynamically built
--  from the same departments array, so they are identical)
-- ============================================================

INSERT INTO departments (id, label, color, sort_order)
VALUES
  ('training',  'Training — Trainers',         '#60a5fa', 1),
  ('sac',       'Service à la clientèle',       '#f472b6', 2),
  ('marketing', 'Marketing',                    '#ff6b35', 3),
  ('sales',     'Sales',                        '#fbbf24', 4)
ON CONFLICT (id) DO UPDATE SET
  label      = EXCLUDED.label,
  color      = EXCLUDED.color,
  sort_order = EXCLUDED.sort_order;

-- ============================================================
-- 2. PEOPLE
-- Column notes:
--   delegate   → delegatable field ('yes','partial','no','unknown')
--   programs   → text[]
--   schedule   → text (free-form)
--   avatar_color    → deterministic color derived from id (see avatarColor fn)
--   avatar_initials → first letter of first + first letter of second word in name
-- ============================================================

-- VP (special record, no reports_to)
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES (
  'vp',
  'You',
  'VP of Training',
  'exec',
  'all',
  NULL,
  ARRAY[]::text[],
  '',
  'no',
  '',
  '#ff6b35',
  'YO',
  0
)
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- Leads
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES
  (
    'L1',
    'Jessica Clermont',
    'Coordonnatrice à la formation',
    'lead',
    'training',
    'vp',
    ARRAY['BSP','RCR','Élite','CV','Drone'],
    'Lun-Ven, jour',
    'partial',
    'Pilier central de l''académie — sans elle, l''académie ne tourne pas. Très fiable, très organisée, proactive, anticipe les problèmes, gère bien les urgences. Gère déjà presque tout sans intervention du VP. La personne la plus importante de l''équipe opérationnelle.',
    '#34d399',
    'JC',
    10
  ),
  (
    'L2',
    'Mitchell Skelton',
    'Technicien service à la clientèle (changement de titre à venir)',
    'lead',
    'training',
    'vp',
    ARRAY['CV'],
    'Lun-Ven 8h-16h30 (employé) + cours CV (contractor)',
    'partial',
    'Seul employé physiquement présent au bureau Montréal Lun-Ven. Pilier opérationnel de l''académie — tout ce qui se passe sur place passe par lui. Très fiable, discret mais ambitieux. Salaire actuel 52 000$ → 57 000$ (bonification +5k assumée par le VP). Changement de titre à discuter.',
    '#60a5fa',
    'MS',
    11
  ),
  (
    'L3',
    'Hamza Maghraoui',
    'Responsable contractuel du service à la clientèle',
    'lead',
    'sac',
    'vp',
    ARRAY['SAC'],
    'Remote — facturation hebdomadaire',
    'yes',
    'En poste depuis 5 jan 2026. Basé Trois-Rivières, travaille entièrement à distance. Très fort profil — gère déjà presque tout sans le VP. Contractor: 23$/h. Préavis 14 jours des deux côtés. NDA + non-concurrence signé.',
    '#a78bfa',
    'HM',
    12
  )
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- Training Contractors & Employees
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES
  (
    't1',
    'Jean Bonnet Lundy',
    'Trainer BSP',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Soir + week-end (flexible) — en continu',
    'no',
    'Très fiable, toujours présent. Ponctuel, autonome, bonne pédagogie, connaît bien son contenu BSP. Trainer stable — pas de velléités de rôle senior.',
    '#fbbf24',
    'JB',
    20
  ),
  (
    't2',
    'Arnaud Deffert',
    'Trainer BSP + Responsable amélioration continue des formations',
    'employee',
    'training',
    'vp',
    ARRAY['BSP'],
    'Jour',
    'yes',
    'EMPLOYÉ (pas contractor). Très fiable, toujours présent. Ses heures entre les cours appartiennent à XGuard — ressource sous-utilisée si on le laisse juste donner des cours. Marge pour lui confier plus sans avoir besoin de son initiative.',
    '#f472b6',
    'AD',
    21
  ),
  (
    't3',
    'Marc Éric Deschambault',
    'Trainer BSP/RCR/Élite/Gestion de crise/Secourisme — Trainer-ambassadeur',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP','RCR','Élite','Gestion de crise','Secourisme'],
    'BSP soir (1 sur 2) / Secourisme 1-2x semaine / Élite 1-2j/sem / Remplacement week-end / Québec occasionnel',
    'yes',
    'Très polyvalent, bon pédagogue, fiable sur la livraison. Vendeur naturel — pousse organiquement formations supplémentaires et équipement en cours. A clairement exprimé intérêt pour rôle plus senior. PAS fiable sur tâches gestion/admin — ne pas lui confier coordination ou suivi admin. Sa valeur est sur le terrain.',
    '#22d3ee',
    'MD',
    22
  ),
  (
    't4',
    'Khaled Deramoune',
    'Trainer RCR / Secourisme',
    'contractor',
    'training',
    'vp',
    ARRAY['RCR'],
    'Jour — 2 formations/semaine',
    'no',
    'Très fiable, toujours présent. Autonome, communique bien, connaît bien son contenu. Pas d''ambition de croissance — il est bien là où il est. Aucune intervention nécessaire.',
    '#f87171',
    'KD',
    23
  ),
  (
    't5',
    'Monia Baraka',
    'Trainer RCR / Secourisme — INACTIVE',
    'contractor',
    'training',
    'vp',
    ARRAY['RCR','Secourisme'],
    'N/A — INACTIVE',
    'no',
    '⛔ NON ACTIVE — a communiqué son intention de se retirer de la formation. Aucune tâche ni cours à lui assigner pour l''instant. À garder dans la liste de contacts pour éventuel retour.',
    '#86efac',
    'MB',
    24
  ),
  (
    't7',
    'Mélina Bédard',
    'Trainer RCR / Secourisme',
    'contractor',
    'training',
    'vp',
    ARRAY['RCR'],
    'Jour — quelques cours/mois',
    'no',
    'Généralement fiable avec quelques absences occasionnelles. Bonne pédagogie, ponctuelle, autonome, communique bien. Pas d''ambition de croissance. Les absences sont à monitorer — si pattern se répète, conversation à avoir via Jessica.',
    '#fdba74',
    'MB',
    25
  ),
  (
    't8',
    'Patrick Bourque',
    'Trainer BSP + Responsable opérations sur place Québec',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Soir — 1 session BSP/mois',
    'yes',
    'Très fiable, toujours présent. Gère déjà de facto toutes les opérations de l''académie à Québec — trainers, salle, logistique. C''est le pilier physique de Québec, l''équivalent de Mitchell à Montréal.',
    '#ff6b35',
    'PB',
    26
  ),
  (
    't9',
    'Mohamed Maghraoui',
    'Trainer BSP',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Week-end — en continu',
    'no',
    'Trainer stable et prévisible. Donne la formation BSP en ligne chaque week-end en continu. Rôle simple et délimité.',
    '#34d399',
    'MM',
    27
  ),
  (
    't10',
    'Bertrand Lauture',
    'Trainer BSP — Backup jour Montréal',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Jour + Soir, flexible — 1 cours en ligne/mois + remplacements',
    'no',
    'Généralement fiable avec quelques absences occasionnelles. Ponctuel, autonome, communique bien. Très pratique comme ressource flexible — backup de jour et disponible pour remplacements. Alt email: bertrandlauture99@gmail.com',
    '#60a5fa',
    'BL',
    28
  ),
  (
    't11',
    'Domingos Oliveira',
    'Trainer BSP + Responsable Division Drone + Responsable Division Élite',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP','Élite','Drone'],
    'Lun-Jeu 9h-16h + soirs Lun-Jeu + week-end (JAMAIS le vendredi)',
    'yes',
    'Très fiable, travaille énormément — pratiquement temps plein contractor. Reporte à VP (résultats divisions) + Jessica (admin, inscriptions, site). Manque d''organisation, se perd dans les détails. A besoin d''une structure claire et d''être montré une ou deux fois — après il est autonome.',
    '#a78bfa',
    'DO',
    29
  ),
  (
    't12',
    'Noureddine Fatnassy',
    'Trainer BSP — Objectif: Secourisme Québec',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Jour — ~1.5 formation BSP/mois',
    'no',
    'Très fiable, toujours présent. Principal point fort : communique bien. Pas particulièrement autonome — a tendance à avoir besoin d''encadrement. Objectif de développement : devenir formateur en Secourisme en milieu de travail à Québec.',
    '#fbbf24',
    'NF',
    30
  ),
  (
    't13',
    'Romann Chapelain',
    'Trainer BSP',
    'contractor',
    'training',
    'vp',
    ARRAY['BSP'],
    'Soir — 1 session BSP/mois',
    'no',
    'Trainer stable et prévisible. Donne une session de gardiennage par mois en ligne le soir. Rôle simple et délimité.',
    '#f472b6',
    'RC',
    31
  ),
  (
    't14',
    'Marie-Claude Gosselin',
    'Trainer RCR/BSP — Potentiel rôle de coordination',
    'contractor',
    'training',
    'vp',
    ARRAY['RCR','BSP'],
    'Jour + Week-end — 4 à 6 cours Secourisme/mois + 1-2 formations BSP/année',
    'yes',
    'Trainer active et fiable. Bon volume de cours. A clairement exprimé intérêt pour évoluer vers un rôle de coordination — la volonté est là. Type de coordination à définir — à explorer en conversation avec elle.',
    '#22d3ee',
    'MG',
    32
  )
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- Service à la clientèle (report to L3 / Hamza)
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES
  (
    's2',
    'Lilia Hassen',
    'Service à la clientèle — Soir semaine',
    'contractor',
    'sac',
    'L3',
    ARRAY['SAC'],
    'Lun-Ven, soir',
    'no',
    'Très fiable, toujours présente. Répond rapidement, bon service client. Respecte parfaitement la structure de reporting — n''a jamais bypassé Hamza. REPORTE À HAMZA UNIQUEMENT — jamais au VP.',
    '#f87171',
    'LH',
    40
  ),
  (
    's3',
    'Sekou Isaint',
    'Service à la clientèle — Week-end',
    'contractor',
    'sac',
    'L3',
    ARRAY['SAC'],
    'Sam-Dim',
    'no',
    'Très fiable, toujours présent. Répond rapidement, bon service client, autonome. Point à corriger : contacte occasionnellement le VP directement en bypassant Hamza — à recadrer par Hamza. REPORTE À HAMZA UNIQUEMENT — jamais au VP.',
    '#86efac',
    'SI',
    41
  )
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- Marketing
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES
  (
    'm1',
    'Alexandre Butterfield',
    'Directeur Marketing / Co-fondateur Dark Horse Ads',
    'lead',
    'marketing',
    'vp',
    ARRAY['MKT'],
    'Always on',
    'no',
    '🔴 Maxed out — ne pas surcharger. Aucune tâche additionnelle pour l''instant. Reçoit les rapports de Hatem et fait le suivi avec lui. Discussions stratégiques avec le VP — il exécute ensuite avec Hatem.',
    '#fdba74',
    'AB',
    50
  ),
  (
    'm2',
    'Hatem Dhaouadi',
    'Automation & Web Builder',
    'contractor',
    'marketing',
    'm1',
    ARRAY['MKT'],
    'When needed → à structurer',
    'no',
    'Généralement fiable avec quelques délais. Exécutant réactif — attend qu''on le contacte. Compétences: automatisation (Zapier, Make), dev web, Go High Level. Reporte à Alex (stratégie) | Jessica (bugs opérationnels, Alex en cc). Le VP ne contacte jamais Hatem directement pour tâches opérationnelles.',
    '#ff6b35',
    'HD',
    51
  )
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- Sales
INSERT INTO people (id, name, role, type, dept, reports_to, programs, schedule, delegate, notes, avatar_color, avatar_initials, sort_order)
VALUES
  (
    'v1',
    'Heidys Garcia',
    'Vendeuse',
    'contractor',
    'sales',
    'vp',
    ARRAY['Sales'],
    '20h/semaine',
    'no',
    '⚠ URGENT: Pas de targets définis, reporte directement au VP. À corriger immédiatement. Très fiable, toujours présente. Fait des appels sortants (cold/warm leads). Aucune cible définie — performance réelle inconnue. Responsable à définir: Jessica ou Mitchell.',
    '#34d399',
    'HG',
    60
  )
ON CONFLICT (id) DO UPDATE SET
  name            = EXCLUDED.name,
  role            = EXCLUDED.role,
  type            = EXCLUDED.type,
  dept            = EXCLUDED.dept,
  reports_to      = EXCLUDED.reports_to,
  programs        = EXCLUDED.programs,
  schedule        = EXCLUDED.schedule,
  delegate        = EXCLUDED.delegate,
  notes           = EXCLUDED.notes,
  avatar_color    = EXCLUDED.avatar_color,
  avatar_initials = EXCLUDED.avatar_initials,
  sort_order      = EXCLUDED.sort_order;

-- ============================================================
-- 3. TASKS
-- tasks field    → jsonb array of {id, text, done}
-- outcomes field → jsonb array of {id, text}
-- expected_outcomes field → jsonb array of {id, text}
-- ============================================================

-- VP
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'vp',
  '[
    {"id":"t_vp1","text":"Conversation avec Jessica — formaliser ownership communication & planification trainers","done":false},
    {"id":"t_vp2","text":"Conversation avec Mitchell — reconnaître rôle, annoncer bonification 5k, décider du titre","done":false},
    {"id":"t_vp3","text":"Conversation avec Hamza — présenter outcomes formalisés Lilia & Sekou","done":false},
    {"id":"t_vp4","text":"Conversation structurée avec Dom — divisions Drone + Élite, seuils, objectifs, compensation","done":false},
    {"id":"t_vp5","text":"Conversation avec Marc Éric — trainer-ambassadeur + décider compensation pour références","done":false},
    {"id":"t_vp6","text":"Conversation avec Patrick — formaliser rôle Responsable Québec + rapport mensuel","done":false},
    {"id":"t_vp7","text":"Conversation avec Arnaud — présenter rôle amélioration continue","done":false},
    {"id":"t_vp8","text":"Conversation avec Noureddine — objectif Secourisme Québec, deadline certification","done":false},
    {"id":"t_vp9","text":"Conversation avec Marie-Claude — explorer quel rôle de coordination lui conviendrait","done":false},
    {"id":"t_vp10","text":"URGENT: Décider à qui Heidys reporte (Jessica ou Mitchell) + briefer ce responsable","done":false},
    {"id":"t_vp11","text":"Aligner avec Alex sur priorités Hatem: (1) tracking ventes, (2) rapport inscriptions automatisé","done":false},
    {"id":"t_vp12","text":"Demander à Hatem — créer système de tracking simple pour références Marc Éric","done":false}
  ]'::jsonb,
  '[
    {"id":"o_vp1","text":"Formation division tourne sans intervention quotidienne du VP"},
    {"id":"o_vp2","text":"Tous les trainers reportent à Jessica — jamais directement au VP"},
    {"id":"o_vp3","text":"Équipe SAC reporte exclusivement à Hamza — jamais au VP"},
    {"id":"o_vp4","text":"Hatem reporte à Alex — le VP ne contacte jamais Hatem directement"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- L1 — Jessica Clermont
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'L1',
  '[
    {"id":"t_l1a","text":"Émettre les certificats du dernier cours","done":false},
    {"id":"t_l1b","text":"Mettre à jour le calendrier sur le portail et le site","done":false},
    {"id":"t_l1c","text":"Envoyer rappels de disponibilité aux trainers (4 mois à l''avance)","done":false},
    {"id":"t_l1d","text":"Coordonner avec Dom (Drone + Élite), Patrick (Québec), Mitchell (logistique Montréal)","done":false}
  ]'::jsonb,
  '[
    {"id":"o_l1a","text":"Gestion de toutes les inscriptions et paiements"},
    {"id":"o_l1b","text":"Émission des certificats"},
    {"id":"o_l1c","text":"Rapport d''inscriptions mensuel livré"},
    {"id":"o_l1d","text":"Suivi des présences de tous les cours"},
    {"id":"o_l1e","text":"Affichage de toutes les dates de formation sur le site"},
    {"id":"o_l1f","text":"Répond à ~95% des courriels entrants"},
    {"id":"o_l1g","text":"Point de contact principal pour tous les étudiants côté admin"},
    {"id":"o_l1h","text":"Gestion des bugs du site et portail — signale directement à Hatem (Alex en cc)"}
  ]'::jsonb,
  '[
    {"id":"e_l1a","text":"Communication & suivi des trainers — ownership complet (point de contact unique pour tous les trainers: absences, disponibilités, confirmations)"},
    {"id":"e_l1b","text":"Tous les trainers communiquent leur disponibilité 3-4 mois à l''avance à Jessica"},
    {"id":"e_l1c","text":"Gestion des remplacements de dernière minute — elle trouve le remplaçant, pas le VP"},
    {"id":"e_l1d","text":"Planification des horaires — ownership complet (tous les programmes planifiés 3-4 mois à l''avance)"},
    {"id":"e_l1e","text":"Calendrier mis à jour en temps réel sur le portail et le site"},
    {"id":"e_l1f","text":"VP n''intervient jamais dans la logistique opérationnelle des trainers"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- L2 — Mitchell Skelton
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'L2',
  '[
    {"id":"t_l2a","text":"Rapport mensuel des commissions envoyé à Jessica pour validation","done":false},
    {"id":"t_l2b","text":"Rapport mensuel opérationnel: état bureau, incidents, besoins identifiés","done":false}
  ]'::jsonb,
  '[
    {"id":"o_l2a","text":"Réceptionne les clients au bureau — 100% ownership"},
    {"id":"o_l2b","text":"Ventes sur place — 100% ownership"},
    {"id":"o_l2c","text":"Traitement de toutes les nouvelles inscriptions et paiements"},
    {"id":"o_l2d","text":"Gestion des remboursements, plaintes et changements de date"},
    {"id":"o_l2e","text":"Traitement des documents pour demandes de permis BSP"},
    {"id":"o_l2f","text":"Gestion complète inventaire uniformes Sécurité XGuard + envois hors région"},
    {"id":"o_l2g","text":"Gestion calendrier CV + remplacements CV"},
    {"id":"o_l2h","text":"Cours CV (contractor)"}
  ]'::jsonb,
  '[
    {"id":"e_l2a","text":"Bureau propre et présentable en tout temps — checklist structurée (quotidien/hebdo/mensuel) maintenue"},
    {"id":"e_l2b","text":"Après chaque cours: salle remise en ordre selon checklist définie"},
    {"id":"e_l2c","text":"Tout problème logistique géré par lui — jamais escaladé au VP"},
    {"id":"e_l2d","text":"Suivi des commissions tenu à jour en temps réel"},
    {"id":"e_l2e","text":"Rapport mensuel opérationnel livré chaque fin de mois"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- L3 — Hamza Maghraoui
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'L3',
  '[
    {"id":"t_l3a","text":"Implanter nouveaux outcomes Lilia & Sekou (no-shows + boîte courriel)","done":false},
    {"id":"t_l3b","text":"Recadrer Sekou sur la structure de reporting — plus de contact direct au VP","done":false},
    {"id":"t_l3c","text":"Développer scripts de réponse standardisés pour toute l''équipe SAC","done":false}
  ]'::jsonb,
  '[
    {"id":"o_l3a","text":"Lilia et Sekou reportent exclusivement à lui — jamais au VP"},
    {"id":"o_l3b","text":"Supervise qualité des réponses aux commentaires réseaux sociaux (SAC en ligne)"},
    {"id":"o_l3c","text":"Gère toutes les plaintes étudiantes complexes — zéro escalade au VP"},
    {"id":"o_l3d","text":"Rapport hebdomadaire SAC au VP — chaque lundi matin (tickets, plaintes, no-shows, courriels, commentaires, points à améliorer)"}
  ]'::jsonb,
  '[
    {"id":"e_l3a","text":"Équipe SAC opère complètement indépendamment du VP"},
    {"id":"e_l3b","text":"Si nouveau agent SAC recruté — onboarding complet géré par lui, zéro implication VP"},
    {"id":"e_l3c","text":"Monitore qualité du service de son équipe en continu"},
    {"id":"e_l3d","text":"Zéro membre de l''équipe SAC ne contacte le VP directement"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- m1 — Alexandre Butterfield
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'm1',
  '[
    {"id":"t_m1a","text":"Aligner avec VP sur priorités Hatem: (1) tracking ventes, (2) rapport inscriptions automatisé","done":false},
    {"id":"t_m1b","text":"Planifier calendrier de campagnes 4 semaines à l''avance","done":false}
  ]'::jsonb,
  '[
    {"id":"o_m1a","text":"Rapport mensuel marketing avec leads & conversion data"},
    {"id":"o_m1b","text":"Calendrier de campagnes planifié 4 semaines à l''avance"},
    {"id":"o_m1c","text":"Reçoit les rapports de Hatem et fait le suivi avec lui"},
    {"id":"o_m1d","text":"Discussions stratégiques avec le VP — exécute ensuite avec Hatem"}
  ]'::jsonb,
  '[
    {"id":"e_m1a","text":"Hatem est entièrement géré par Alex — VP ne contacte jamais Hatem directement"},
    {"id":"e_m1b","text":"Système de tracking ventes opérationnel pour Marc Éric et Heidys"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- m2 — Hatem Dhaouadi
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'm2',
  '[
    {"id":"t_m2a","text":"Créer système de tracking simple pour références Marc Éric et Heidys","done":false},
    {"id":"t_m2b","text":"Automatiser rapport mensuel inscriptions — livré automatiquement à Jessica","done":false}
  ]'::jsonb,
  '[
    {"id":"o_m2a","text":"Site web maintenu à jour en tout temps"},
    {"id":"o_m2b","text":"Toutes les automatisations GHL maintenues et fonctionnelles"},
    {"id":"o_m2c","text":"Portail étudiants maintenu et amélioré en continu"}
  ]'::jsonb,
  '[
    {"id":"e_m2a","text":"Tout bug ou panne résolu dans les 24h suivant le signalement de Jessica"},
    {"id":"e_m2b","text":"Système de tracking des ventes opérationnel (priorité)"},
    {"id":"e_m2c","text":"Rapport mensuel inscriptions automatisé livré à Jessica"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t1 — Jean Bonnet Lundy
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't1',
  '[]'::jsonb,
  '[
    {"id":"o_t1a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t1b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t1c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t2 — Arnaud Deffert
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't2',
  '[]'::jsonb,
  '[
    {"id":"o_t2a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t2b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t2c","text":"Amélioration continue des formations — les jours sans cours, analyse contenu BSP et identifie améliorations"},
    {"id":"o_t2d","text":"Standardise et améliore la façon dont les rapports de cours sont faits par les autres trainers"}
  ]'::jsonb,
  '[
    {"id":"e_t2a","text":"Au moins 1 proposition concrète d''amélioration par mois à Jessica ou au VP (format: quoi changer, pourquoi, comment)"},
    {"id":"e_t2b","text":"Les jours sans cours = temps d''analyse et propositions, pas du temps libre"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t3 — Marc Éric Deschambault
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't3',
  '[]'::jsonb,
  '[
    {"id":"o_t3a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t3b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t3c","text":"À chaque cours: présenter activement le Programme Élite aux étudiants BSP éligibles"},
    {"id":"o_t3d","text":"Mentionner systématiquement les formations complémentaires (Gestion de crise, Secourisme, etc.)"},
    {"id":"o_t3e","text":"Rapport mensuel simple: références et ventes générées — envoyé à Jessica"}
  ]'::jsonb,
  '[
    {"id":"e_t3a","text":"Référer les ventes d''équipement via lien ou code trackable créé par Hatem"},
    {"id":"e_t3b","text":"Aucune coordination de trainers / Aucune tâche administrative / Aucun suivi d''inscriptions"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t4 — Khaled Deramoune
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't4',
  '[]'::jsonb,
  '[
    {"id":"o_t4a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t4b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t4c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t5 — Monia Baraka
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't5',
  '[]'::jsonb,
  '[]'::jsonb,
  '[
    {"id":"e_t5a","text":"⛔ INACTIVE — aucune tâche ni cours à assigner. À garder en contact pour éventuel retour."}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t7 — Mélina Bédard
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't7',
  '[]'::jsonb,
  '[
    {"id":"o_t7a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t7b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t7c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[
    {"id":"e_t7a","text":"Absences à monitorer — si pattern se répète, conversation via Jessica"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t8 — Patrick Bourque
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't8',
  '[]'::jsonb,
  '[
    {"id":"o_t8a","text":"1 session BSP par mois à Québec (soir)"},
    {"id":"o_t8b","text":"Coordination des autres professeurs à Québec"},
    {"id":"o_t8c","text":"Gestion de la salle et de la logistique sur place"},
    {"id":"o_t8d","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t8e","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"}
  ]'::jsonb,
  '[
    {"id":"e_t8a","text":"Rapport mensuel opérationnel Québec — envoyé au VP chaque dernier vendredi du mois (tâches, état salle, trainers Québec, points à améliorer)"},
    {"id":"e_t8b","text":"Gestion générale des opérations de l''académie à Québec — ownership complet"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t9 — Mohamed Maghraoui
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't9',
  '[]'::jsonb,
  '[
    {"id":"o_t9a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t9b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t9c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t10 — Bertrand Lauture
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't10',
  '[]'::jsonb,
  '[
    {"id":"o_t10a","text":"1 cours BSP en ligne par mois, le soir"},
    {"id":"o_t10b","text":"Backup pour les cours de jour en présentiel à Montréal"},
    {"id":"o_t10c","text":"Disponibilité pour remplacements confirmée rapidement quand Jessica le contacte"},
    {"id":"o_t10d","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t10e","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t11 — Domingos Oliveira
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't11',
  '[]'::jsonb,
  '[
    {"id":"o_t11a","text":"Division Drone — ownership complet: ventes, classes, annulations, rescédulations"},
    {"id":"o_t11b","text":"Planifie toutes les dates de classes Drone avec Jessica — elle affiche sur le site"},
    {"id":"o_t11c","text":"Gère le seuil minimum d''inscriptions par classe — annule et rescédule si non atteint"},
    {"id":"o_t11d","text":"Division Élite — ownership complet de la croissance et pérennité du programme (99$/mois)"},
    {"id":"o_t11e","text":"Responsable de faire grossir le nombre d''abonnés actifs Élite"},
    {"id":"o_t11f","text":"Formation BSP en ligne en continu — soirs Lun-Jeu + week-end"},
    {"id":"o_t11g","text":"Rapport mensuel au VP: classes livrées, inscriptions, annulations, revenus générés (Drone + Élite)"}
  ]'::jsonb,
  '[
    {"id":"e_t11a","text":"Zéro décision opérationnelle Drone qui remonte au VP"},
    {"id":"e_t11b","text":"Rapport mensuel livré proactivement — format exact à être montré une fois par le VP"},
    {"id":"e_t11c","text":"Seuil minimum d''inscriptions + objectif ventes mensuel Drone + Élite à définir avec VP"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t12 — Noureddine Fatnassy
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't12',
  '[
    {"id":"t_t12a","text":"S''inscrire lui-même à la certification Secourisme — deadline à fixer","done":false}
  ]'::jsonb,
  '[
    {"id":"o_t12a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t12b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t12c","text":"Formation BSP à Québec — ~1.5 formation/mois"}
  ]'::jsonb,
  '[
    {"id":"e_t12a","text":"Devenir formateur en Secourisme en milieu de travail à Québec (objectif de développement)"},
    {"id":"e_t12b","text":"Revenir avec un plan de match sans que le VP ait à relancer"},
    {"id":"e_t12c","text":"Une fois certifié: gérer son propre calendrier Secourisme à Québec"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t13 — Romann Chapelain
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't13',
  '[]'::jsonb,
  '[
    {"id":"o_t13a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t13b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t13c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- t14 — Marie-Claude Gosselin
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  't14',
  '[]'::jsonb,
  '[
    {"id":"o_t14a","text":"Rapport de présence envoyé à Jessica après chaque cours"},
    {"id":"o_t14b","text":"Disponibilité communiquée 3-4 mois à l''avance à Jessica"},
    {"id":"o_t14c","text":"Tout imprévu ou absence signalé à Jessica directement — jamais au VP"}
  ]'::jsonb,
  '[
    {"id":"e_t14a","text":"Explorer quel rôle de coordination lui conviendrait (pistes: trainers RCR Montréal, remplacements, backup)"},
    {"id":"e_t14b","text":"Potentiel: onboarding nouveaux trainers si rôle de coordination confirmé"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- s2 — Lilia Hassen
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  's2',
  '[]'::jsonb,
  '[
    {"id":"o_s2a","text":"Toutes les demandes étudiantes des soirs de semaine traitées dans les 24h"},
    {"id":"o_s2b","text":"Escalade vers Hamza uniquement — jamais vers le VP, sans exception"},
    {"id":"o_s2c","text":"Résumé des tickets envoyé à Hamza chaque vendredi soir"},
    {"id":"o_s2d","text":"No-shows Secourisme en semaine — ownership complet: appel immédiat à tous les absents, objectif recéduler avec frais 50$"},
    {"id":"o_s2e","text":"Boîte courriel formations — gère les soirs de semaine, répond aux questions standards, escalade à Hamza si dépassé"}
  ]'::jsonb,
  '[
    {"id":"e_s2a","text":"Suivi des no-shows et résultats envoyé à Hamza chaque vendredi soir"},
    {"id":"e_s2b","text":"Zéro contact direct avec le VP — tout passe par Hamza"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- s3 — Sekou Isaint
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  's3',
  '[]'::jsonb,
  '[
    {"id":"o_s3a","text":"Toutes les demandes étudiantes du week-end traitées dans les 24h"},
    {"id":"o_s3b","text":"Escalade vers Hamza uniquement — jamais vers le VP, sans exception"},
    {"id":"o_s3c","text":"Résumé des tickets week-end envoyé à Hamza chaque dimanche soir"},
    {"id":"o_s3d","text":"No-shows Secourisme le week-end — ownership complet: appel immédiat à tous les absents, objectif recéduler avec frais 50$"},
    {"id":"o_s3e","text":"Boîte courriel formations — gère le week-end, répond aux questions standards, escalade à Hamza si dépassé"}
  ]'::jsonb,
  '[
    {"id":"e_s3a","text":"Suivi des no-shows et résultats envoyé à Hamza chaque dimanche soir"},
    {"id":"e_s3b","text":"⚠ À recadrer: ne plus contacter le VP directement — tout passe par Hamza"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- v1 — Heidys Garcia
INSERT INTO tasks (person_id, tasks, outcomes, expected_outcomes)
VALUES (
  'v1',
  '[
    {"id":"t_v1a","text":"Décider du responsable de Heidys (Jessica ou Mitchell) — URGENT","done":false},
    {"id":"t_v1b","text":"Laisser tourner 2-3 semaines pour établir baseline avant de fixer des targets","done":false}
  ]'::jsonb,
  '[
    {"id":"o_v1a","text":"Appels sortants (cold/warm leads) — 20h/semaine"}
  ]'::jsonb,
  '[
    {"id":"e_v1a","text":"Rapport hebdomadaire obligatoire envoyé à son responsable chaque vendredi: appels effectués, ventes conclues, heures travaillées, suivis, 2e calls, overview semaine"},
    {"id":"e_v1b","text":"Targets à définir après évaluation baseline: appels sortants minimum/semaine, leads contactés minimum, taux de conversion cible"},
    {"id":"e_v1c","text":"Reporte à Jessica ou Mitchell — plus jamais directement au VP"}
  ]'::jsonb
)
ON CONFLICT (person_id) DO UPDATE SET
  tasks             = EXCLUDED.tasks,
  outcomes          = EXCLUDED.outcomes,
  expected_outcomes = EXCLUDED.expected_outcomes;

-- ============================================================
-- END OF SEED
-- ============================================================
-- Summary:
--   departments : 4 rows
--   people      : 23 rows (1 VP + 3 leads + 13 training + 2 SAC + 2 marketing + 1 sales + 1 marketing lead already counted)
--   tasks       : 22 rows (one per person who has task data defined)
-- ============================================================
