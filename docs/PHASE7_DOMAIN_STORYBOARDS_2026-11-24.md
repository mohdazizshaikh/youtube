# Phase 7 — offline domain storyboard reconstruction

Base: GitHub `db1f527a6372ada41871ddbe73dd41865c33ae7d`. The interrupted earlier Phase 7 had notes and two sample images, but no verified patch in the repository. This increment is a fresh reproducible implementation, not a claim of recovery of the unavailable source bytes.

## Operator workflow

From the repository root, install requirements in an isolated Python environment. The storyboard CLI makes no network calls and performs no account actions.

```powershell
python -m tools.domain_storyboard --demo-all --animatics --output-dir outputs/domain-demo-v1
python -m tools.domain_storyboard --input outputs/domain-demo-v1/sports_short/input.json --output-dir outputs/single-review-v1
```

Omit `--animatics` if FFmpeg with libx264 is not installed. Use a new output directory per run; an existing directory is rejected. `--demo-all` generates 24 synthetic inputs (12 domains × SHORT/LONG), board PNGs, manifests and optional 3-second silent MP4s. Each manifest binds the validated input, PNG and, if produced, the MP4 with SHA-256. Font and codec versions can affect the output bytes. Inspect every output before reuse.

For real draft preparation, replace the synthetic title/claims/sources/locators/specialist fields with human-supplied records and set `synthetic_demo` to false. Each claim needs supporting sources with a declared primary record, two different groups and hosts, and specific locators. Declared refutations must first receive human resolution. The renderer rejects invalid links, repeated source IDs/URLs, absent specialist fields, and text that does not fit. It intentionally accepts only printable ASCII text at this stage; no Hindi or complex-script rendering acceptance is claimed.

Original diagram primitives are illustrative, not data-driven charts or external media. PNGs use portrait 720×1280 or landscape 1280×720. MP4s are silent 3-second fade animatics in those same dimensions. All are marked NOT FACT / RIGHTS CLEARED. HTTPS syntax, group names and host diversity do not prove real source reliability or independence. The tool cannot verify external facts, legal permissions, semantic accuracy, speaker identity or publication readiness. It does not modify upload gates, schemas, owner data, or the 24-video acceptance matrix. It is not a full creative director, a finished film generator, or a licensed voice pipeline.

## Remaining dependencies

The owner must provide any missing historical backup, licensed Hindi/English models and real audio, annotated reference timings, authorized YouTube OAuth/channel access, physical Windows PC and actual source/rights review. Full domain production, 24 accepted original films, real GPU generation and authenticated Analytics experiments remain outstanding. Synthetic output is not accepted video evidence.
