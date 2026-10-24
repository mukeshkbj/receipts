CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  brief TEXT NOT NULL,
  category TEXT,
  status TEXT NOT NULL DEFAULT 'running',
  requirements TEXT,
  brief_json TEXT,
  error TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trace (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ts REAL NOT NULL,
  stage TEXT NOT NULL,
  event TEXT NOT NULL,
  detail TEXT DEFAULT '',
  actor TEXT DEFAULT 'system'
);

CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  name TEXT NOT NULL,
  vendor TEXT DEFAULT '',
  homepage TEXT DEFAULT '',
  category TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  incumbent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id),
  type TEXT NOT NULL,
  text TEXT NOT NULL,
  source_url TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  claim_id INTEGER NOT NULL REFERENCES claims(id),
  check_name TEXT NOT NULL,
  kind TEXT NOT NULL,
  url TEXT DEFAULT '',
  excerpt TEXT DEFAULT '',
  measured_value TEXT DEFAULT '',
  supports INTEGER
);

CREATE TABLE IF NOT EXISTS verdicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  claim_id INTEGER NOT NULL REFERENCES claims(id),
  verdict TEXT NOT NULL,
  confidence REAL DEFAULT 0.5,
  rationale TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id),
  req_key TEXT NOT NULL,
  score REAL NOT NULL,
  weight REAL NOT NULL,
  rationale TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS outreach (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id),
  subject TEXT DEFAULT '',
  body TEXT DEFAULT '',
  questions TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ts REAL NOT NULL,
  model TEXT NOT NULL,
  purpose TEXT NOT NULL,
  in_tok INTEGER DEFAULT 0,
  out_tok INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS watches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  snapshot TEXT DEFAULT '{}',
  created_at REAL NOT NULL,
  last_check REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  watch_id INTEGER NOT NULL REFERENCES watches(id),
  run_id TEXT NOT NULL,
  ts REAL NOT NULL,
  check_name TEXT DEFAULT '',
  summary TEXT DEFAULT '',
  detail TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_trace_run ON trace(run_id, id);
CREATE INDEX IF NOT EXISTS idx_claims_cand ON claims(run_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_claim ON verdicts(claim_id);
CREATE INDEX IF NOT EXISTS idx_usage_run ON usage(run_id);
CREATE INDEX IF NOT EXISTS idx_alerts_watch ON alerts(watch_id);
