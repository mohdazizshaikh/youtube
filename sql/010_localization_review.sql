-- Immutable, review-gated human-created locale variants. No machine translation.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS m25_localized_variants (
 variant_id TEXT PRIMARY KEY,
 project_id TEXT NOT NULL REFERENCES content_projects(project_id) ON DELETE CASCADE,
 script_version_id TEXT NOT NULL REFERENCES scripts(script_version_id),
 source_script_sha256 TEXT NOT NULL CHECK(length(source_script_sha256)=64),
 dependency_sha256 TEXT NOT NULL CHECK(length(dependency_sha256)=64),
 locale TEXT NOT NULL CHECK(locale IN ('hi-IN','en-IN','en-US')),
 content_json TEXT NOT NULL CHECK(json_valid(content_json)),
 content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
 status TEXT NOT NULL CHECK(status IN ('PENDING_OWNER_REVIEW','OWNER_REVIEWED')),
 reviewer TEXT,
 reviewed_at TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(project_id,script_version_id,locale)
);
CREATE INDEX IF NOT EXISTS idx_m25_localized_project ON m25_localized_variants(project_id,created_at);
