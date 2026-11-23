-- Additive M3.2: one append-only, owner-supervised recovery event per unknown upload.
-- Contains hashes of public remote identifiers, NOT OAuth credentials.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS m32_remote_reconciliations (
 reconciliation_id TEXT PRIMARY KEY,
 intent_id TEXT NOT NULL UNIQUE REFERENCES m3_private_upload_intents(intent_id),
 video_id_sha256 TEXT NOT NULL CHECK(length(video_id_sha256)=64),
 verification_sha256 TEXT NOT NULL CHECK(length(verification_sha256)=64),
 reviewer TEXT NOT NULL,
 observed_at_utc TEXT NOT NULL,
 owner_studio_attested INTEGER NOT NULL CHECK(owner_studio_attested=1),
 readonly_oauth_verified INTEGER NOT NULL CHECK(readonly_oauth_verified=1),
 created_at TEXT NOT NULL
);
