# SESSION CLOSEOUT — HM12 (HL-MULTIKEY-CHAT-001)

**PTH:** HM12 | **Sprint:** Multi-Key Detection + Song-Aware Theory Chat | **Date:** 2026-03-22

## Summary
HarmonyLab v2.18.0 → v2.18.1. Two fixes: (1) multi-key region detection broken because `_parse_chord()` didn't handle iReal/MuseScore chord notation; (2) Theory Chat now song-aware — sends song title, key center regions, and chord sequence with every request.

## Root Cause (BV-01 fail)
`_parse_chord()` checked `is_minor = quality.startswith('m')` — but iReal/MuseScore imports use `-` for minor (D-9, B-7, A-7). So all minor chords were flagged as non-minor. Without minor ii chords, `detect_ii_v_i_patterns()` found 0 patterns. With `pattern_keys` empty, all chords assigned to home key → 1 region.

Also: `^` notation for maj7 (C^9 = Cmaj9) wasn't handled.

## Fixes Applied

### key_center_service.py — `_parse_chord()` notation handling
- `is_minor`: now also checks `quality.startswith('-')` (D-9, B-7, A-7)
- `is_maj7`: now also checks `quality.startswith('^')`, `quality == 't7'` (C^9, At7)
- `is_half_dim`: now also checks `'-7b5'` in quality
- `is_dom7`: now also handles `'9sus'`/`'13sus'` prefixes

### key_center_service.py — Sliding window fallback (Step 2.5)
When `len(pattern_keys) < 2` (pattern detection didn't find multiple keys), score all 24 keys against windows of 4 chords and add discovered keys to `pattern_keys`. Ensures multi-region detection even for non-standard progressions.

### analysis.py — Song-aware theory chat
`TheoryChatRequest.song_context` now processed for: `title`, `key`, `key_centers` (with measure ranges), `chord_sequence`, `current_chord`/`current_measure`. Context response now leads with song identity, key regions, and chord list before jazz theory RAG snippets.

### song.html — sendTheoryChat() enriched
Sends `songData.title`, `keyCenterData.regions`, first 16 chords from `analysisData.chords` in `song_context`.

## Result
Song 95 (Corcovado): was **1 region** (C major, confidence 0.5), now **3 regions**:
- C major: measures 2-9 (confidence 0.8 — pattern-backed)
- A major: measures 11-13 (confidence 0.8 — pattern-backed)
- C major: measures 14-30 (confidence 0.5 — assignment-based)

Patterns detected: ii-V-I in C (D-9/G13/C^9), ii-V-I in C (D-9/G7b9/C6), ii-V-I in A (B-7/E7/At7)

## Files Changed
- `app/services/key_center_service.py` — _parse_chord() + sliding window
- `app/api/routes/analysis.py` — song-aware theory chat context
- `frontend/song.html` — sendTheoryChat() enriched + v2.18.1
- `frontend/nginx.conf`, `index.html`, `quiz.html`, `progress.html`, `audit.html`, `riffs.html` — v2.18.1
- `main.py` — VERSION = "2.18.1"

## Deploy
- Commit: `6aa74af`
- Backend: CI/CD push to main → harmonylab deployed v2.18.1
- Frontend: gcloud run deploy harmonylab-frontend → `harmonylab-frontend-00091-22z` SUCCESS

## Canary Results
- C1 (BV-01): PASS — song 95 returns 3 key regions: C major mm2-9, A major mm11-13, C major mm14-30
- C2 (BV-02): PASS — theory-chat response shows "Corcovado", key center regions with measure ranges, chord sequence
- C3 (BV-03): PASS — GET /health returns version 2.18.1
- C4: PASS — live song.html shows v2.18.1 in nav

## MetaPM
- Handoff ID: D0FAB749-5291-4EC4-9C28-3FB3300A7426
- UAT Spec: 8709F899-CE88-45DA-871E-9DCA7CFA526D
- UAT URL: https://metapm.rentyourcio.com/uat/8709F899-CE88-45DA-871E-9DCA7CFA526D

## PL Actions Required
- BV-01: Load Corcovado → confirm 2+ key regions visible in kc-debug text above chord grid
- BV-02: Open Theory Chat → ask "Why does this song have two key centers?" → confirm response shows song name, measure ranges, and chord sequence

## Lessons Learned
- iReal/MuseScore chord imports use `-` for minor, `^` for maj7 — always check notation variants when chord parsing feeds algorithmic logic
- "1 region, confidence 0.5" = no patterns detected, not a key scoring issue — check the parsing layer first
- Sliding window fallback is a safety net; fixing the parser is the real fix
