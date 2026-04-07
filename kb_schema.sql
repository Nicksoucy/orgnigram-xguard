-- ============================================================
-- XGuard Knowledge Base Schema — 4 tables
-- Run once in Supabase SQL Editor
-- ============================================================

-- 1. Raw analyzed emails (one row per email)
CREATE TABLE IF NOT EXISTS kb_emails (
  id              BIGSERIAL PRIMARY KEY,
  email_msg_id    TEXT NOT NULL UNIQUE,           -- Message-ID header (dedup key)
  folder          TEXT,
  from_addr       TEXT,
  subject         TEXT,
  email_date      TIMESTAMPTZ,
  body_preview    TEXT,                            -- first 500 chars of body
  category        TEXT,                            -- inscription|info|paiement|plainte|annulation|changement_date|certificat|emploi|technique|spam|autre
  question        TEXT,                            -- main client question (or null)
  intent          TEXT,                            -- what client wants
  urgency         TEXT,                            -- haute|moyenne|basse
  needs_response  BOOLEAN DEFAULT true,
  suggested_response TEXT,                         -- Haiku suggested answer
  faq_topic       TEXT,                            -- raw topic string from Haiku
  topic_id        TEXT,                            -- FK to kb_topics.topic_id (set by aggregator)
  batch_id        TEXT,                            -- which analyzer run
  analyzed_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kb_emails_category ON kb_emails(category);
CREATE INDEX IF NOT EXISTS idx_kb_emails_faq_topic ON kb_emails(faq_topic);
CREATE INDEX IF NOT EXISTS idx_kb_emails_topic_id ON kb_emails(topic_id);
CREATE INDEX IF NOT EXISTS idx_kb_emails_analyzed_at ON kb_emails(analyzed_at);
CREATE INDEX IF NOT EXISTS idx_kb_emails_needs_response ON kb_emails(needs_response) WHERE needs_response = true;

-- 2. Canonical FAQ topics (aggregated from raw emails)
CREATE TABLE IF NOT EXISTS kb_topics (
  id                BIGSERIAL PRIMARY KEY,
  topic_id          TEXT NOT NULL UNIQUE,           -- slug like "inscription-en-ligne"
  category          TEXT NOT NULL,                   -- inscription|paiement|annulation|...
  topic_label       TEXT NOT NULL,                   -- human readable label
  question_pattern  TEXT,                            -- canonical question pattern
  suggested_response TEXT,                           -- best AI response (or Nick's corrected version)
  frequency         INTEGER DEFAULT 0,              -- total emails matching this topic
  example_subjects  TEXT[],                          -- top 5 real email subjects
  example_emails    JSONB,                           -- top 3 email snippets [{subject, from, body_preview, date}]
  approval_status   TEXT DEFAULT 'pending',          -- pending|approved|rejected|corrected
  approved_by       TEXT,
  approved_at       TIMESTAMPTZ,
  nick_correction   TEXT,                            -- Nick's corrected response (if corrected)
  merged_raw_topics TEXT[],                          -- which raw faq_topic strings map here
  first_seen        TIMESTAMPTZ DEFAULT now(),
  last_seen         TIMESTAMPTZ DEFAULT now(),
  last_aggregated   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_kb_topics_category ON kb_topics(category);
CREATE INDEX IF NOT EXISTS idx_kb_topics_approval ON kb_topics(approval_status);
CREATE INDEX IF NOT EXISTS idx_kb_topics_frequency ON kb_topics(frequency DESC);

-- 3. Approval audit log (immutable)
CREATE TABLE IF NOT EXISTS kb_approvals (
  id                BIGSERIAL PRIMARY KEY,
  topic_id          TEXT NOT NULL,
  action            TEXT NOT NULL,                   -- approve|reject|correct
  previous_response TEXT,                            -- what the response was before
  corrected_response TEXT,                           -- Nick's correction (if action=correct)
  action_by         TEXT DEFAULT 'nick',
  action_at         TIMESTAMPTZ DEFAULT now(),
  source            TEXT DEFAULT 'admin_page'        -- admin_page|email|api
);

CREATE INDEX IF NOT EXISTS idx_kb_approvals_topic ON kb_approvals(topic_id);
CREATE INDEX IF NOT EXISTS idx_kb_approvals_date ON kb_approvals(action_at DESC);

-- 4. Run log (operational monitoring)
CREATE TABLE IF NOT EXISTS kb_run_log (
  id                BIGSERIAL PRIMARY KEY,
  script            TEXT NOT NULL,                   -- kb_email_analyzer|kb_topic_aggregator|kb_approval_email
  batch_id          TEXT,
  started_at        TIMESTAMPTZ DEFAULT now(),
  finished_at       TIMESTAMPTZ,
  emails_fetched    INTEGER DEFAULT 0,
  emails_analyzed   INTEGER DEFAULT 0,
  emails_failed     INTEGER DEFAULT 0,
  topics_created    INTEGER DEFAULT 0,
  topics_updated    INTEGER DEFAULT 0,
  status            TEXT DEFAULT 'running',           -- running|completed|failed|paused
  error_msg         TEXT,
  details           JSONB                             -- extra info
);

-- Enable realtime for admin page
ALTER PUBLICATION supabase_realtime ADD TABLE kb_topics;
ALTER PUBLICATION supabase_realtime ADD TABLE kb_approvals;
