-- =============================================
-- XGuard Scheduling Schema
-- Generated: 2026-03-16
-- Based on: Horaire v3 (1).xlsx + existing people table
-- =============================================
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING
-- =============================================

-- Enable extension required for TSRANGE exclusion constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- =============================================
-- 1. LOCATIONS
-- 4 salles Montréal (in-class), 1 salle Québec, 1 Online
-- Sourced from: formation en classe MTL, Formation Québec, Formation Ligne sheets
-- =============================================
CREATE TABLE IF NOT EXISTS locations (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  code        TEXT UNIQUE NOT NULL,
  city        TEXT NOT NULL DEFAULT 'Montreal',
  is_virtual  BOOLEAN DEFAULT false,
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT now()
);

INSERT INTO locations (name, code, city, is_virtual) VALUES
  ('Salle 1 — Montréal',  'MTL-S1',  'Montreal', false),
  ('Salle 2 — Montréal',  'MTL-S2',  'Montreal', false),
  ('Salle 3 — Montréal',  'MTL-S3',  'Montreal', false),
  ('Salle 4 — Montréal',  'MTL-S4',  'Montreal', false),
  ('Salle Québec',        'QC-S1',   'Quebec',   false),
  ('En ligne',            'ONLINE',  'Virtual',  true)
ON CONFLICT (code) DO NOTHING;

-- =============================================
-- 2. COHORTS
-- Cohort codes found in Excel:
--
-- Formation Québec (sheet):
--   J# series      → BSP jour, présentiel Québec (e.g. J10–J29)
--   QC# series     → BSP jour Québec (QC1–QC14)
--   QCS# series    → BSP soir Québec (QCS1–QCS16)
--   WK# series     → BSP weekend Québec (WK1–WK2)
--   MNJ# series    → Marc Noël Jour (MNJ5)
--
-- Formation en classe MTL (sheet):
--   J# series      → BSP jour classe Montréal (J4–J63)
--   S# series      → BSP soir classe Montréal (S1–S33)
--   W# series      → BSP weekend classe Montréal (W1–W26)
--
-- Formation Ligne (sheet):
--   JL# series     → BSP jour en ligne (JL5–JL58)
--   LS# series     → BSP soir en ligne (LS1–LS38)
--   LW# series     → BSP weekend en ligne (LW15–LW29)
--   LJ# series     → BSP jour (ligne, Antonio weekend format) (LJ4–LJ9)
--   L# series      → BSP ligne générale (L10–L66)
--   A# series      → Anglais BSP (A4–A8)
--   AS# series     → Anglais BSP soir (AS1–AS12)
--   AW# series     → Anglais BSP weekend (AW1)
--   WK# series     → BSP weekend ligne (WK6–WK8)
--   W# series      → Weekend ligne (W1–W21)
--   QC# series     → Québec en ligne (QCJ20–QCJ24)
--   MNJ# series    → Marc Noël Jour en ligne (MNJ1–MNJ5)
--   M# series      → Marc général (M1–M2)
--
-- RCR Montréal (sheet):
--   Numeric        → RCR cohort sessions (numbered 1–n per trainer per cycle)
--   LW# series     → LW23 appears (ligne weekend RCR)
--
-- Status codes found in cells:
--   F → Férié (holiday / unavailable)
--   E → En vacances / Excused
--   R → Remplacement (needs replacement)
--   I → Indisponible
--   V → Vacances
--   x → Absent / blocked
--   CANCEL → Cancelled
-- =============================================
CREATE TABLE IF NOT EXISTS cohorts (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code             TEXT UNIQUE NOT NULL,
  -- Program: 'BSP', 'RCR', 'Elite', 'Drone', 'Secourisme', 'Anglais'
  program          TEXT NOT NULL,
  -- Shift: 'jour', 'soir', 'weekend'
  shift_type       TEXT NOT NULL CHECK (shift_type IN ('jour', 'soir', 'weekend')),
  -- Delivery: 'ligne' (online), 'classe' (in-person MTL), 'presentiel_qc' (in-person QC)
  delivery_mode    TEXT NOT NULL CHECK (delivery_mode IN ('ligne', 'classe', 'presentiel_qc')),
  -- Sequence number extracted from code (e.g. 43 from J43)
  cohort_number    INTEGER,
  -- Optional date range populated as cohort progresses
  start_date       DATE,
  end_date         DATE,
  total_weeks      INTEGER,
  current_students INTEGER DEFAULT 0,
  min_students     INTEGER DEFAULT 5,
  notes            TEXT,
  is_active        BOOLEAN DEFAULT true,
  created_at       TIMESTAMPTZ DEFAULT now()
);

-- =============================================
-- 3. SCHEDULE ENTRIES
-- Main scheduling table — one row per instructor-day assignment
-- instructor_id references the existing people.id text keys (e.g. 't3', 't4')
-- =============================================
CREATE TABLE IF NOT EXISTS schedule_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- FK to existing people table (text pk: 'vp','L1','t1','t2', etc.)
  instructor_id   TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
  cohort_id       UUID REFERENCES cohorts(id) ON DELETE SET NULL,
  location_id     UUID NOT NULL REFERENCES locations(id),
  program         TEXT NOT NULL,   -- 'BSP','RCR','Elite','Drone','Secourisme','Anglais'
  -- Category maps to which Excel sheet this came from:
  -- 'formation_qc'    → Formation Québec sheet
  -- 'rcr_mtl'         → RCR Montréal sheet
  -- 'classe_mtl'      → Formation en classe MTL sheet
  -- 'formation_ligne' → Formation Ligne sheet
  category        TEXT NOT NULL CHECK (category IN (
    'formation_qc', 'rcr_mtl', 'classe_mtl', 'formation_ligne'
  )),
  shift_type      TEXT NOT NULL CHECK (shift_type IN ('jour', 'soir', 'weekend')),
  date            DATE NOT NULL,
  start_time      TIME NOT NULL,
  end_time        TIME NOT NULL,
  -- Computed from date + start_time/end_time via trigger below
  time_range      TSRANGE,
  -- Status mirrors cell codes from Excel:
  -- 'scheduled'  → cohort code in cell (e.g. J43, LS12, QCS7)
  -- 'confirmed'  → confirmed by instructor
  -- 'holiday'    → F (Férié)
  -- 'vacation'   → V (Vacances) / E (Excusé)
  -- 'unavailable'→ I (Indisponible) / x
  -- 'replacement'→ R (remplacement needed)
  -- 'cancelled'  → CANCEL
  -- 'completed'  → after the date has passed
  status          TEXT DEFAULT 'scheduled' CHECK (status IN (
    'scheduled','confirmed','holiday','vacation',
    'unavailable','replacement','cancelled','completed'
  )),
  -- Raw cell code from the Excel for traceability (e.g. 'J43', 'QCS7', 'LS22', 'F', 'R')
  excel_cell_code TEXT,
  topic           TEXT,
  notes           TEXT,
  created_by      TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Trigger: automatically compute time_range from date + start_time/end_time
CREATE OR REPLACE FUNCTION compute_time_range()
RETURNS TRIGGER AS $$
BEGIN
  NEW.time_range := tsrange(
    (NEW.date + NEW.start_time)::timestamp,
    (NEW.date + NEW.end_time)::timestamp,
    '[)'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_compute_time_range ON schedule_entries;
CREATE TRIGGER trg_compute_time_range
  BEFORE INSERT OR UPDATE ON schedule_entries
  FOR EACH ROW EXECUTE FUNCTION compute_time_range();

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_schedule_updated_at ON schedule_entries;
CREATE TRIGGER trg_schedule_updated_at
  BEFORE UPDATE ON schedule_entries
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================
-- 4. SCHEDULE TEMPLATES
-- Reusable weekly patterns per program/shift/category
-- pattern JSONB example:
-- {
--   "days_of_week": [1,2,3,4],         -- 0=Sun 1=Mon ... 6=Sat
--   "start_time": "09:00",
--   "end_time": "17:00",
--   "frequency": "weekly",             -- 'weekly' | 'biweekly'
--   "sessions_per_cohort": 10          -- typical cohort length in days
-- }
-- =============================================
CREATE TABLE IF NOT EXISTS schedule_templates (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  program     TEXT NOT NULL,
  category    TEXT NOT NULL CHECK (category IN (
    'formation_qc', 'rcr_mtl', 'classe_mtl', 'formation_ligne'
  )),
  shift_type  TEXT NOT NULL CHECK (shift_type IN ('jour', 'soir', 'weekend')),
  pattern     JSONB NOT NULL,
  notes       TEXT,
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Seed common templates observed in Excel
INSERT INTO schedule_templates (name, program, category, shift_type, pattern) VALUES
  (
    'BSP Jour — Classe MTL (Lun–Ven)',
    'BSP', 'classe_mtl', 'jour',
    '{"days_of_week":[1,2,3,4,5],"start_time":"08:30","end_time":"16:30","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'BSP Soir — Classe MTL (Lun–Ven)',
    'BSP', 'classe_mtl', 'soir',
    '{"days_of_week":[1,2,3,4,5],"start_time":"18:00","end_time":"22:00","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'BSP Weekend — Classe MTL (Sam–Dim)',
    'BSP', 'classe_mtl', 'weekend',
    '{"days_of_week":[6,0],"start_time":"08:30","end_time":"16:30","frequency":"weekly","sessions_per_cohort":5}'
  ),
  (
    'BSP Jour — En ligne (Lun–Ven)',
    'BSP', 'formation_ligne', 'jour',
    '{"days_of_week":[1,2,3,4,5],"start_time":"09:00","end_time":"17:00","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'BSP Soir — En ligne (Lun–Ven)',
    'BSP', 'formation_ligne', 'soir',
    '{"days_of_week":[1,2,3,4,5],"start_time":"18:00","end_time":"22:00","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'BSP Weekend — En ligne (Sam–Dim)',
    'BSP', 'formation_ligne', 'weekend',
    '{"days_of_week":[6,0],"start_time":"09:00","end_time":"17:00","frequency":"weekly","sessions_per_cohort":5}'
  ),
  (
    'BSP Jour — Formation Québec (Lun–Ven)',
    'BSP', 'formation_qc', 'jour',
    '{"days_of_week":[1,2,3,4,5],"start_time":"08:30","end_time":"16:30","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'BSP Soir — Formation Québec (Lun–Ven)',
    'BSP', 'formation_qc', 'soir',
    '{"days_of_week":[1,2,3,4,5],"start_time":"18:00","end_time":"22:00","frequency":"weekly","sessions_per_cohort":10}'
  ),
  (
    'RCR — Montréal (Jour, 2 jours/session)',
    'RCR', 'rcr_mtl', 'jour',
    '{"days_of_week":[1,2,3,4,5],"start_time":"08:30","end_time":"16:30","frequency":"biweekly","sessions_per_cohort":2}'
  ),
  (
    'RCR — Montréal Soir (2 soirs/session)',
    'RCR', 'rcr_mtl', 'soir',
    '{"days_of_week":[1,2,3,4,5],"start_time":"18:00","end_time":"22:00","frequency":"biweekly","sessions_per_cohort":2}'
  )
ON CONFLICT DO NOTHING;

-- =============================================
-- 5. AVAILABILITIES
-- Instructor availability overrides (absences, holidays, vacations)
-- Mirrors the status codes from the Excel (F, V, E, I, x)
-- =============================================
CREATE TABLE IF NOT EXISTS availabilities (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  instructor_id   TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  date            DATE NOT NULL,
  is_available    BOOLEAN DEFAULT true,
  -- reason mirrors Excel codes: 'ferie','vacances','excused','indisponible','autre'
  reason          TEXT CHECK (reason IN (
    'ferie','vacances','excused','indisponible','replacement_needed','autre'
  )),
  notes           TEXT,
  UNIQUE (instructor_id, date)
);

-- =============================================
-- 6. REPLACEMENTS
-- Tracks replacement requests (cells marked R or CANCEL in Excel)
-- =============================================
CREATE TABLE IF NOT EXISTS replacements (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schedule_entry_id         UUID NOT NULL REFERENCES schedule_entries(id) ON DELETE CASCADE,
  original_instructor_id    TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
  replacement_instructor_id TEXT REFERENCES people(id) ON DELETE SET NULL,
  reason                    TEXT NOT NULL,
  -- status: 'pending' → replacement needed, 'filled' → replacement assigned, 'cancelled' → entry cancelled
  status                    TEXT DEFAULT 'pending' CHECK (status IN (
    'pending','filled','cancelled'
  )),
  requested_at              TIMESTAMPTZ DEFAULT now(),
  resolved_at               TIMESTAMPTZ,
  notes                     TEXT
);

-- =============================================
-- 7. ROW LEVEL SECURITY
-- All tables open (internal tool, no auth layer)
-- =============================================
ALTER TABLE locations        ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohorts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE availabilities   ENABLE ROW LEVEL SECURITY;
ALTER TABLE replacements     ENABLE ROW LEVEL SECURITY;

-- Drop and recreate policies to avoid duplicate errors on re-run
DO $$
BEGIN
  -- locations
  DROP POLICY IF EXISTS "public all" ON locations;
  CREATE POLICY "public all" ON locations FOR ALL USING (true) WITH CHECK (true);

  -- cohorts
  DROP POLICY IF EXISTS "public all" ON cohorts;
  CREATE POLICY "public all" ON cohorts FOR ALL USING (true) WITH CHECK (true);

  -- schedule_entries
  DROP POLICY IF EXISTS "public all" ON schedule_entries;
  CREATE POLICY "public all" ON schedule_entries FOR ALL USING (true) WITH CHECK (true);

  -- schedule_templates
  DROP POLICY IF EXISTS "public all" ON schedule_templates;
  CREATE POLICY "public all" ON schedule_templates FOR ALL USING (true) WITH CHECK (true);

  -- availabilities
  DROP POLICY IF EXISTS "public all" ON availabilities;
  CREATE POLICY "public all" ON availabilities FOR ALL USING (true) WITH CHECK (true);

  -- replacements
  DROP POLICY IF EXISTS "public all" ON replacements;
  CREATE POLICY "public all" ON replacements FOR ALL USING (true) WITH CHECK (true);
END $$;

-- =============================================
-- 8. INDEXES
-- =============================================
CREATE INDEX IF NOT EXISTS idx_schedule_entries_instructor_date
  ON schedule_entries (instructor_id, date);

CREATE INDEX IF NOT EXISTS idx_schedule_entries_cohort
  ON schedule_entries (cohort_id);

CREATE INDEX IF NOT EXISTS idx_schedule_entries_location_date
  ON schedule_entries (location_id, date);

CREATE INDEX IF NOT EXISTS idx_schedule_entries_date
  ON schedule_entries (date);

CREATE INDEX IF NOT EXISTS idx_schedule_entries_category
  ON schedule_entries (category);

CREATE INDEX IF NOT EXISTS idx_availabilities_instructor_date
  ON availabilities (instructor_id, date);

CREATE INDEX IF NOT EXISTS idx_cohorts_program
  ON cohorts (program, shift_type, delivery_mode);

-- =============================================
-- 9. REALTIME
-- =============================================
ALTER PUBLICATION supabase_realtime ADD TABLE locations;
ALTER PUBLICATION supabase_realtime ADD TABLE cohorts;
ALTER PUBLICATION supabase_realtime ADD TABLE schedule_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE availabilities;
ALTER PUBLICATION supabase_realtime ADD TABLE replacements;

-- =============================================
-- 10. INSTRUCTOR → PEOPLE TABLE MAPPING
-- Excel name → people.id (existing table)
-- =============================================
-- Formation Québec sheet trainers:
--   Nicolas             → vp   (VP / Nicolas)
--   Mélina              → t7   (Mélina Bédard)
--   Marc Noel / Marc noel → (not in people table — external QC trainer)
--   Marc-Éric / Marc eric → t3   (Marc Éric Deschambault)
--   Patrick / Partrick  → t8   (Patrick Bourque)
--   Jérémie             → (not in people table)
--   Marc Baudet         → (not in people table)
--   Mélina RCR          → t7   (Mélina Bédard)
--   Marc-Eric RCR       → t3   (Marc Éric Deschambault)
--   Nouredinne          → t12  (Noureddine Fatnassy)
--   Marie claude        → t14  (Marie-Claude Gosselin)
--   Jean-daniel / jean daniel → (not in people table)
--   Mahdi Mkaouar       → (not in people table)
--
-- RCR Montréal sheet trainers:
--   Khaled              → t4   (Khaled Deramoune)
--   Boualem             → (not in people table)
--   Marc eric           → t3   (Marc Éric Deschambault)
--   Monia / MOnia       → t5   (Monia Baraka — INACTIVE)
--   Jacques             → (not in people table)
--   Antonio             → (not in people table — possibly t11 Domingos? No, separate)
--   Khaled soir         → t4   (Khaled Deramoune, evening slot)
--   Sophie Poirier      → (not in people table)
--   Marie Claude        → t14  (Marie-Claude Gosselin)
--   Mohamed             → t9   (Mohamed Maghraoui)
--
-- Formation en classe MTL sheet trainers:
--   Jean luc            → (not in people table — "Jean luc" likely Jean Luc Rioux or similar)
--   Jean Bonnet         → t1   (Jean Bonnet Lundy)
--   Mitchell            → L2   (Mitchell Skelton)
--   MOhamed / Mohamed   → t9   (Mohamed Maghraoui)
--   Marie               → t14  (Marie-Claude Gosselin)
--   Bertrand            → t10  (Bertrand Lauture)
--   Bertan/Marie-Claude → t10 + t14 (split assignment)
--   Marc                → t3   (Marc Éric Deschambault)
--   A confirmer         → TBD
--
-- Formation Ligne sheet trainers:
--   Antonio BSP Weekend → (not in people table as "Antonio")
--   Antonio BSP soir    → (same as above)
--   Arnaud              → t2   (Arnaud Deffert)
--   Allette             → (not in people table)
--   Marc eric           → t3   (Marc Éric Deschambault)
--   Marc Noel           → (not in people table — Marc Noël, QC trainer)
--   Mathieu Busseau     → (not in people table)
--   Marc Noel soir      → (same Marc Noël)
--   Anglais option jour → language program, instructor TBD
--   Anglais option soir → language program, instructor TBD
--   Anglais option WK   → language program, instructor TBD
--   Mitchell            → L2   (Mitchell Skelton)
--   Arnaud Jour         → t2   (Arnaud Deffert)
--   Marc eric Soir      → t3   (Marc Éric Deschambault)
--   Marc Noel jour et wk → Marc Noël
--   Domingos Oliveira   → t11  (Domingos Oliveira)
--   Romann              → t13  (Romann Chapelain)
--   Mohamed Maghraoui   → t9   (Mohamed Maghraoui)
--   Bertran             → t10  (Bertrand Lauture)
--   Marc eric jour      → t3
--   Marc eric soir      → t3
-- =============================================

-- =============================================
-- END OF SCHEMA
-- =============================================
-- Quick-reference cohort code legend:
--
-- PREFIX  | PROGRAM | SHEET           | SHIFT    | DELIVERY
-- --------|---------|-----------------|----------|-----------
-- J##     | BSP     | classe_mtl      | jour     | classe
-- S##     | BSP     | classe_mtl      | soir     | classe
-- W##     | BSP     | classe_mtl      | weekend  | classe
-- QC##    | BSP     | formation_qc    | jour     | presentiel_qc
-- QCS##   | BSP     | formation_qc    | soir     | presentiel_qc
-- WK##    | BSP     | formation_qc    | weekend  | presentiel_qc
-- JL##    | BSP     | formation_ligne | jour     | ligne
-- LS##    | BSP     | formation_ligne | soir     | ligne
-- LW##    | BSP     | formation_ligne | weekend  | ligne
-- LJ##    | BSP     | formation_ligne | weekend  | ligne (Antonio)
-- L##     | BSP     | formation_ligne | various  | ligne
-- A##     | Anglais | formation_ligne | jour     | ligne
-- AS##    | Anglais | formation_ligne | soir     | ligne
-- AW##    | Anglais | formation_ligne | weekend  | ligne
-- MNJ##   | BSP     | formation_ligne | jour     | ligne (Marc Noël)
-- QCJ##   | BSP     | formation_ligne | jour     | presentiel_qc
-- RCR#    | RCR     | rcr_mtl         | jour/soir| classe
-- =============================================
