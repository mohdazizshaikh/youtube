-- M2.4 opt-in local acoustic-alignment drafts. Never overwrite M2.2 owner-reviewed alignments.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS m24_alignment_drafts (
 draft_id TEXT PRIMARY KEY,
 plan_id TEXT NOT NULL REFERENCES m2_studio_plans(plan_id) ON DELETE CASCADE,
 project_id TEXT NOT NULL REFERENCES content_projects(project_id) ON DELETE CASCADE,
 script_version_id TEXT NOT NULL REFERENCES scripts(script_version_id),
 plan_sha256 TEXT NOT NULL CHECK(length(plan_sha256)=64),
 voice_sha256 TEXT NOT NULL CHECK(length(voice_sha256)=64),
 locale TEXT NOT NULL,
 model_name TEXT NOT NULL,
 words_json TEXT NOT NULL CHECK(json_valid(words_json)),
 status TEXT NOT NULL CHECK(status IN ('PENDING_OWNER_REVIEW','OWNER_REVIEWED_IMPORTED')),
 created_at TEXT NOT NULL,
 reviewed_at TEXT,
 UNIQUE(plan_id,plan_sha256,voice_sha256)
);
CREATE INDEX IF NOT EXISTS idx_m24_draft_project ON m24_alignment_drafts(project_id,created_at);
