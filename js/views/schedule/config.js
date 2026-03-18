// ==================== SCHEDULE: CONFIG ====================

// ---- Constants ----

const SCHED_MONTHS_FR = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
const SCHED_DAYS_FR   = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];

const SCHED_STATUS_LABELS = {
  scheduled:   'Planifié',
  confirmed:   'Confirmé',
  holiday:     'Férié',
  vacation:    'Vacances',
  unavailable: 'Indisponible',
  replacement: 'Remplacement',
  cancelled:   'Annulé'
};

const SCHED_STATUS_COLORS = {
  scheduled:   '#3b82f6',
  confirmed:   '#10b981',
  holiday:     '#374151',
  vacation:    '#1e3a5f',
  unavailable: '#374151',
  replacement: '#78350f',
  cancelled:   '#7f1d1d'
};

// Default program colors fallback (overridden by DB data)
const SCHED_DEFAULT_PROGRAM_COLORS = {
  'BSP':           '#3b82f6',
  'RCR':           '#f97316',
  'ELITE':         '#8b5cf6',
  'DRONE':         '#f97316',
  'SECOURISME':    '#ef4444',
  'CV_PLACEMENT':  '#06b6d4',
  'GESTION_CRISE': '#dc2626',
  'ANGLAIS_BSP':   '#f59e0b',
  'SAC':           '#f472b6',
  'COORDINATION':  '#64748b',
  'VENTES':        '#fbbf24',
  'RECRUTEMENT':   '#a78bfa',
  'FILMAGE':       '#7c3aed'
};

// ---- Jours fériés Québec (fixes + Pâques calculé) ----

// Returns the nth occurrence of a weekday (0=Sun…6=Sat) in a given month/year
function nthWeekday(year, month, weekday, n) {
  const d = new Date(year, month - 1, 1);
  // Advance to first occurrence of weekday
  const diff = (weekday - d.getDay() + 7) % 7;
  d.setDate(1 + diff + (n - 1) * 7);
  return d;
}

function schedGetHolidaysQC(year) {
  // Calcul Pâques (algorithme Anonymous Gregorian)
  function easter(y) {
    const a = y % 19, b = Math.floor(y/100), c = y % 100;
    const d = Math.floor(b/4), e = b % 4, f = Math.floor((b+8)/25);
    const g = Math.floor((b-f+1)/3), h = (19*a+b-d-g+15) % 30;
    const i = Math.floor(c/4), k = c % 4;
    const l = (32+2*e+2*i-h-k) % 7;
    const m = Math.floor((a+11*h+22*l)/451);
    const month = Math.floor((h+l-7*m+114)/31);
    const day   = ((h+l-7*m+114) % 31) + 1;
    return new Date(y, month-1, day);
  }
  const e = easter(year);
  const addDays = (d, n) => { const r = new Date(d); r.setDate(r.getDate()+n); return r; };
  const fmt = d => d.toISOString().slice(0,10);

  return new Set([
    `${year}-01-01`,                    // Jour de l'An
    fmt(addDays(e, -2)),                // Vendredi Saint
    // Lundi de Pâques retiré — XGuard travaille ce jour
    fmt(nthWeekday(year, 5, 1, 3)),     // Journée nationale des patriotes (3e lundi mai)
    `${year}-06-24`,                    // Fête nationale Québec
    `${year}-07-01`,                    // Fête du Canada
    fmt(nthWeekday(year, 8, 1, 1)),     // Congé civique (1er lundi août)
    fmt(nthWeekday(year, 9, 1, 1)),     // Fête du Travail (1er lundi sept)
    fmt(nthWeekday(year, 10, 1, 2)),    // Action de grâce (2e lundi oct)
    `${year}-11-11`,                    // Jour du Souvenir
    `${year}-12-25`,                    // Noël
    `${year}-12-26`,                    // Lendemain de Noël
  ]);
}

// ---- Cohort patterns ----

const SCHED_COHORT_PATTERNS = {
  'BSP_SOIR': {
    label:      'BSP Soir (Lun-Jeu, 3 semaines)',
    program:    'BSP',
    shift_type: 'soir',
    days:       [1,2,3,4],   // Lun=1,Mar=2,Mer=3,Jeu=4 (JS getDay)
    sessions:   12,
    start_time: '18:00',
    end_time:   '22:00',
    gap_days:   4,            // jours de pause entre cohortes (après dernier jour)
    prefix:     'JS',
  },
  'BSP_JOUR': {
    label:      'BSP Jour (Lun-Ven, 3 semaines)',
    program:    'BSP',
    shift_type: 'jour',
    days:       [1,2,3,4,5],
    sessions:   15,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   2,
    prefix:     'J',
  },
  'BSP_JOUR_8J': {
    label:      'BSP Jour — 8 jours ouvrables',
    program:    'BSP',
    shift_type: 'jour',
    days:       [1,2,3,4,5],  // Lun-Ven, any start day
    sessions:   8,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   2,
    prefix:     'QC',
    consecutive: true,        // flag: skip weekends+holidays only, no fixed day restriction
  },
  'BSP_JOUR_7J': {
    label:      'BSP Jour — 7 jours ouvrables',
    program:    'BSP',
    shift_type: 'jour',
    days:       [1,2,3,4,5],
    sessions:   7,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   2,
    prefix:     'QC',
    consecutive: true,
  },
  'BSP_WEEKEND': {
    label:      'BSP Weekend (Sam-Dim, 4 weekends)',
    program:    'BSP',
    shift_type: 'weekend',
    days:       [6,0],        // Sam=6, Dim=0
    sessions:   8,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   0,
    prefix:     'W',
  },
  'RCR': {
    label:      'RCR (2 jours — Sam+Dim)',
    program:    'RCR',
    shift_type: 'jour',
    days:       [6,0],        // Samedi + Dimanche
    sessions:   2,
    consecutive: true,        // 2 jours consécutifs
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   0,
    prefix:     'RCR',
  },
  'RCR_1J': {
    label:      'RCR (1 journée — Samedi)',
    program:    'RCR',
    shift_type: 'jour',
    days:       [6],
    sessions:   1,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   0,
    prefix:     'RC',
  },
  'ELITE': {
    label:      'Élite (Lun-Jeu, 2 semaines)',
    program:    'ELITE',
    shift_type: 'jour',
    days:       [1,2,3,4],
    sessions:   8,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   3,
    prefix:     'E',
  },
  'ALTERNATING': {
    label:      'Alterné (2 groupes de jours)',
    program:    'BSP',
    shift_type: 'jour',
    days:       [],           // handled specially by alternating logic
    sessions:   0,
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   0,
    prefix:     'MC',
    alternating: true,        // flag for special rendering
  },
  'GESTION_CRISE_BIWEEKLY': {
    label:      'Gestion de Crise (1 Lundi sur 2)',
    program:    'GESTION_CRISE',
    shift_type: 'jour',
    days:       [1],          // Lundi seulement
    sessions:   1,            // 1 session à la fois
    start_time: '09:00',
    end_time:   '17:00',
    gap_days:   13,           // 13 jours de pause = prochain lundi dans 2 semaines
    prefix:     'GC',
    biweekly:   true,
  },
};

// Location ID for Salle Québec
const SCHED_LOCATION_QC = '680eacdc-2975-4e7d-a80c-e944b7ae4df6';
