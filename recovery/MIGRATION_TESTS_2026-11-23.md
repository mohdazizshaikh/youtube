# Offline migration test evidence — 2026-11-23

- Host: Linux container, Python 3.13, FFmpeg and pytest; NOT the target Windows desktop.
- `python -m pytest -q`: **51 passed in 24.55 seconds** (exit 0).
- `python tools/verify_package.py`: **PASS: verified 280 package file hashes** after restoring original README and .gitignore (exit 0).
- `node --check app/static/app.js`: **PASS** (exit 0).
- No real-account OAuth, upload, Analytics, GPU or Windows acceptance tests were performed.
- Actual publishing remains PRIVATE-only opt-in.
