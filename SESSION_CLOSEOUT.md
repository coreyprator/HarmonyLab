# SESSION_CLOSEOUT.md — HL-REGRESSIONS-001 (PTH-HM03)

> **Sprint ID**: HL-REGRESSIONS-001
> **Session Date**: 2026-03-14
> **Version**: v2.11.0 → v2.12.0
> **Bootstrap**: v1.5.8
> **Backend URL**: https://harmonylab-wmrla7fhwa-uc.a.run.app

---

## Deliverables

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Fix 1: Note count badges in both views | DONE | Removed currentView gate, API returns note_count for all chords |
| 2 | Fix 2: Transpose flat spelling | DONE | Eb13=III13 (was D#13=#II13), AbMaj9=VIMaj9 (was G#Maj9=#VMaj9) |
| 3 | Fix 3: Score playback rework | DONE | togglePlayPause reloads scorePart, play button shows Score label |
| 4 | v2.12.0 deployed | DONE | Backend harmonylab-00161-xh5, Frontend harmonylab-frontend-00079-wz4 |
| 5 | Canary 5/5 | PASS | Version, note counts, transpose, notes endpoint |
| 6 | UAT submitted | DONE | 16747974-8919-4378-B87A-228AF4FA2D04 |

---

## Commits

| SHA | Description |
|-----|-------------|
| `50e827e` | v2.12.0: HL-REGRESSIONS-001 — transpose spelling, score playback, note count badge |
| `6875ef1` | docs: update PROJECT_KNOWLEDGE.md for v2.12.0 |

---

## MetaPM Handoff

- UAT ID: 16747974-8919-4378-B87A-228AF4FA2D04
- Handoff ID: F5420FB7-8354-4BCD-8151-2476114EF7D4

Full details: `handoffs/outbox/SESSION_CLOSEOUT_2026-03-14.md`
