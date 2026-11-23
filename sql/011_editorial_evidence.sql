-- Additive non-publishing human editorial attestations. Never infer copyright clearance.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS m26_editorial_reviews (
 review_id TEXT PRIMARY KEY,
 project_id TEXT NOT NULL REFERENCES content_projects(project_id) ON DELETE CASCADE,
 script_version_id TEXT NOT NULL REFERENCES scripts(script_version_id),
 final_export_id TEXT NOT NULL REFERENCES m22_final_exports(export_id),
 dependency_sha256 TEXT NOT NULL CHECK(length(dependency_sha256)=64),
 auditor TEXT NOT NULL,
 decision TEXT NOT NULL CHECK(decision='OWNER_REVIEWED_NOT_LEGALLY_CERTIFIED'),
 notes TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(project_id,final_export_id,dependency_sha256)
);
CREATE INDEX IF NOT EXISTS idx_m26_editorial_reviews ON m26_editorial_reviews(project_id,created_at);
