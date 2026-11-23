# M3.2 — Supervised REMOTE_UNKNOWN private upload reconciliation

**No new video is uploaded by this tool.** A failed resumable `videos.insert` request can leave the remote result uncertain. Blind retry could duplicate the same content. ViralOS preserves the `REMOTE_UNKNOWN` intent until the owner locates the exact video in YouTube Studio and checks privacy/identity.

## Operator procedure

1. On the **owner's machine**, open YouTube Studio for the authorized channel. Identify the existing video ID; confirm it belongs to the intended owner channel and is set **PRIVATE**. Check kids/synthetic disclosures, title, description, tags, rights warnings and any other Studio-only indicators.
2. Ensure owner-upload OAuth exists in the OS keyring. Set `VIRALOS_ENABLE_M32_READONLY_CHECK=1` **only during** the supervised check. Do not copy client secrets or tokens into the repository.
3. Execute the CLI with **all explicit confirmations**:

```powershell
$env:VIRALOS_ENABLE_M32_READONLY_CHECK = '1'
python tools/m32_reconcile_unknown.py --intent-id YOUR_EXISTING_INTENT_ID `
  --video-id ABCDEFGHIjk --reviewer 'Owner' `
  --confirm-readonly-network I_AUTHORIZE_READONLY_CHECK `
  --confirm-checked-studio I_CHECKED_PRIVATE_AND_DISCLOSURE `
  --confirm-reconcile I_RECONCILE_EXISTING_INTENT_ONLY `
  --evidence-output C:\Private\viralos-m32-reconcile-NEW.json
```

The CLI performs read-only `channels.list(mine=true)` and `videos.list` through existing OAuth infrastructure, compares to exact stored intent fields, and refuses mismatched channel, video ID, nonprivate status, absent owner confirmation or non-`REMOTE_UNKNOWN` intents. No retry, upload, delete, scheduling or privacy edit occurs.

On valid matching evidence, one SQLite transaction records a **single reconciliation event** (`sql/013_remote_unknown_reconciliation.sql`) with hashed video ID and verification data, and changes the original intent to `UPLOADED_PRIVATE`. The normal existing final editorial approval and real Analytics acceptance requirements are **not** waived. Local evidence must stay private. This transaction is not a YouTube API mutation.

**Important:** This implements the code path and synthetic tests, *not* an actual account validation. No real YouTube session ran in this engineering phase. Do not claim final `M3.2` acceptance unless the owner physically completes this procedure plus the regular acceptance checklist.
