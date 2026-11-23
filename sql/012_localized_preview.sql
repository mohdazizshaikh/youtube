-- Owner-reviewed locale -> owner narration -> actual CPU technical preview.
-- Never an upload approval, licensed-voice assertion or final publishable export.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS m25_localized_previews (
 preview_id TEXT PRIMARY KEY,
 project_id TEXT NOT NULL REFERENCES content_projects(project_id) ON DELETE CASCADE,
 variant_id TEXT NOT NULL REFERENCES m25_localized_variants(variant_id) ON DELETE CASCADE,
 source_dependency_sha256 TEXT NOT NULL CHECK(length(source_dependency_sha256)=64),
 variant_content_sha256 TEXT NOT NULL CHECK(length(variant_content_sha256)=64),
 plan_sha256 TEXT NOT NULL CHECK(length(plan_sha256)=64),
 voice_sha256 TEXT NOT NULL CHECK(length(voice_sha256)=64),
 voice_origin TEXT NOT NULL,
 owner_voice_rights_attested INTEGER NOT NULL CHECK(owner_voice_rights_attested=1),
 preview_file_relpath TEXT NOT NULL,
 preview_file_sha256 TEXT NOT NULL CHECK(length(preview_file_sha256)=64),
 quality_json TEXT NOT NULL CHECK(json_valid(quality_json)),
 status TEXT NOT NULL CHECK(status='TECHNICAL_PREVIEW_OWNER_REVIEW_REQUIRED'),
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_m25_localized_previews_project ON m25_localized_previews(project_id,created_at);
