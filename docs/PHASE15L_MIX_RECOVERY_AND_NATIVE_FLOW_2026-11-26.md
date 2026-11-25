# Phase 15L — paired mixed recovery and native flow preview

Phase 15K verified CI 45699538573 at c604c82ea594f43da9ddad14e184ac875269e1bc: Linux 1103 passed, 796 hashes verified; Windows 977 passed, 60 skipped. Phase 15J static regression passed in the full suite. New Phase 15L CI pending.

## Paired mixed production recovery

Stop all review consoles. Archive both mixed production children (their complete pilot files and exact SQLite bytes), both mix.json receipts and pair_mix.json in one private snapshot. Independent snapshot pin, paired receipt pin and child pins; check child manifest and video SHA, file inventory, queue states, and re-audit original inputs before and after backup. Restore to a separate directory, rewriting only child catalogs as in pilot_snapshot, preserving review history and original receipts; fresh paired remix and media verification after restoration. Metadata-only verify does not decode media. The original parent pair/native derivative, both music files, original mix request and source font/request or bundle inputs must be retained separately. No encryption, concurrent writer or power loss guarantee; never overwrite a destination.

```
python -m tools.paired_mix_snapshot backup --pair /private/pair --pair-sha256 PIN --request /private/paired-mix.json --request-sha256 PIN --hindi-music /private/hi.wav --english-music /private/en.wav --mixed /private/mixed --pair-mix-sha256 MIX_PIN --snapshot /private/snapshot
python -m tools.paired_mix_snapshot verify --snapshot /private/snapshot --snapshot-sha256 SNAP_PIN --pair-mix-sha256 MIX_PIN
python -m tools.paired_mix_snapshot restore --pair /private/pair --pair-sha256 PIN --request /private/paired-mix.json --request-sha256 PIN --hindi-music /private/hi.wav --english-music /private/en.wav --mixed /private/restored --pair-mix-sha256 MIX_PIN --snapshot /private/snapshot --snapshot-sha256 SNAP_PIN
```
Optional --native and --native-sha256 select native Hindi. Mixed child queues remain independent; mixed dashboard/transaction orchestration pending.

## Native flow diagram preview

Standalone three-step Devanagari flow diagram, vertical SHORT (720x1280) or horizontal LONG (1280x720), with native RAQM glyph shaping, pinned licensed font declaration, source declaration SHA-256, distinct ordered labels, explicit bounds and no silent font fallback. Request fields: schema VIRALOS_NATIVE_FLOW_DIAGRAM_REQUEST_V1, locale hi-IN, format SHORT/LONG, font_sha256, font_rights_attested true, license_reference, source_declaration_sha256, title, nodes [{step:1,label:...},{step:2,label:...},{step:3,label:...}]. Text must pass existing typography checks. Refuses oversized text instead of clipping. Source declaration pin is a declaration, not verification of content or causal relations. 
```
python -m tools.native_flow_diagram --font /private/font.ttf --font-sha256 PIN --request /private/diagram.json --request-sha256 PIN --output /private/diagram.png
```
PNG report binds request/font/source declarations and glyph bounds. No video integration, arbitrary charts, motion, translation, visual acceptance or legal font certification. Re-render with same environment to compare bytes. No font bundled; Linux CI uses its installed test font. No publication or production merge.
