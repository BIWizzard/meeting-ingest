# Discovery

- Recorded at: 2026-07-30T02:47:19.365Z
- Workstream: dogfood-hardening

The non-receipt-managed Codex skill pair drifted undetected for three days (installed copy stuck at guidance 1.0 from 2026-07-26 while the repo source moved to 1.1 on 2026-07-29). Receipt management is what caught nothing here: the Claude pair verified clean via readiness and runtime inspect, while the Codex pair has no mechanism and only fails a manual cmp that nothing runs automatically.
