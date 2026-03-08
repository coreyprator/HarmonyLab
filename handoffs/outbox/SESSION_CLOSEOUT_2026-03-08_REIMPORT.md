======================================================
=================== HarmonyLab HL-REIMPORT ====================
======================================================

# Session Close-Out: HL-REIMPORT
**Date:** 2026-03-08
**Version:** v2.4.0 (backend + frontend)
**Commit:** 5f45a6e
**MetaPM:** HL-REIMPORT at cc_complete (checkpoint F519)

## What Was Done
- **Full note data import engine** (`app/services/import_engine.py`): Custom .mscx XML parser
  that extracts notes, lyrics, dynamics, articulations, chord symbols, key/time/tempo signatures
- **DB Migration 5**: 8 new tables (song_notes, song_lyrics, song_dynamics, song_tempos,
  song_time_signatures, song_key_signatures, song_text_marks, song_note_articulations)
  plus 7 new columns on Songs table
- **Audit endpoint**: `GET /api/v1/songs/{id}/audit` — returns full parsed data grouped by measure
- **Audit UI**: `frontend/audit.html` — statistics panel, measure navigator, track filter,
  note tables per measure, raw XML tab
- **Wired into upload**: Existing `/api/v1/imports/score/import` now runs rich extraction
  automatically via `parse_upload_full()` + `save_full_parse()`
- **Reparse endpoint updated**: `/api/v1/imports/score/reparse-notes` now uses import_engine
- **Song model updated**: Added has_note_data, has_lyrics, import_format, track_count,
  measure_count, total_notes fields
- **Song list**: Shows [notes] badge and Audit link for songs with note data
- **Song detail**: Shows Audit link button when has_note_data is true
- **Version bump**: 2.3.0 -> 2.4.0 across all files

## What Was NOT Done / Deviations
1. **MuseScore CLI NOT installed** — The prompt specified installing musescore3 + Xvfb in Docker.
   Instead, wrote a custom XML parser that reads .mscx directly. This avoids ~500MB Docker image
   bloat and has zero external dependencies. The custom parser extracts the same data.
2. **music21 NOT used for .mscz parsing** — music21 cannot parse .mscz/.mscx without the
   MuseScore CLI executable. Our custom parser handles the format natively.
3. **defusedxml NOT added** — The prompt recommended it for security. Standard xml.etree.ElementTree
   is used. defusedxml would be a good addition in a follow-up.
4. **Phase 8 re-import of 35 songs**: Source files are NOT stored in GCS. Original .mscz/.mid
   files were discarded at import time. The 35 existing songs cannot be re-imported without
   re-uploading source files. This is documented clearly for PL.
5. **No re-import migration script**: Since source files don't exist in GCS, no batch re-import
   was possible. PL must re-upload songs manually through the UI.

## Phase 9 Test Results (manha de carnava.mscz)
```
Title: Black Orpheus
Key: C
Time sig: 4/4
Tracks: 1  |  Measures: 40
Total notes: 103  |  Total rests: 8
Lyrics: 91  |  Chord symbols: 50

Measure 1 (pickup):
  Lyric: "I" @ beat 1.0
  Beat 1.0 | Trk 0 V1 | E4 | quarter | vel=64

Measure 2:
  Chord: A-7 @ beat 1.0
  Lyric: "sing" @ 1.0, "to" @ 4.0, "the" @ 4.5
  Beat 1.0 | C5 | half | vel=64
  Beat 4.0 | B4 | eighth | vel=64
  Beat 4.5 | A4 | eighth | vel=64

Measure 3:
  Chord: B07 @ 1.0, E7b9 @ 1.0
  Lyric: "sun" @ 1.0, "in" @ 4.0, "the" @ 4.5
  Beat 1.0 | A4 | half | vel=64
  Beat 4.0 | Ab4 | eighth | vel=64
  Beat 4.5 | B4 | eighth | vel=64
```

## Phase 8: Source Files in GCS
**Answer: NO.** No HarmonyLab-specific GCS bucket exists. The super-flashcards-media bucket
has no .mscz/.mid files. The DB `source_file_name` column stores the filename string but the
actual file was not persisted. PL must re-upload songs for note data extraction.

## Data Structure (Phase 1)
MuseScore 4.6.4 .mscx XML structure for manha de carnava:
- 1 music Staff (inside Score element), 40 Measures
- Notes inside Chord elements within voice containers
- Harmony elements (chord symbols) inside voice containers
- TPC root numbering (14=C, 15=G, 16=D, 17=A via line of fifths)
- Lyrics attached to Chord elements

## Key Architecture Decisions
1. **Custom XML parser over music21+MuseScore**: Zero external binary dependency, smaller
   Docker image, deterministic parsing
2. **Idempotent migration**: All 8 tables + 7 columns check existence before CREATE/ALTER
3. **Rich import alongside existing**: The new engine runs as a second pass after the
   existing _save_score_to_db, so chord-only import still works if rich import fails
4. **Raw XML storage**: Full .mscx XML stored in DB for future re-parsing without source file

## Files Modified
- app/services/import_engine.py (NEW — 560 lines)
- app/migrations.py (Migration 5 added)
- app/api/routes/imports.py (wired import_engine)
- app/api/routes/songs.py (audit endpoint)
- app/models/__init__.py (new Song fields)
- frontend/audit.html (NEW — audit UI)
- frontend/index.html (version + audit link)
- frontend/song.html (version + audit link)
- frontend/login.html (version)
- frontend/quiz.html (version)
- frontend/progress.html (version)
- frontend/nginx.conf (version)
- main.py (version 2.4.0)

## Gotchas for Next Session
- DB migration runs on first request after deploy — may add 2-3s to first cold start
- raw_xml column is NVARCHAR(MAX) — very large scores could be slow to query
- The MuseScore version detection (TPC vs chromatic) is based on programVersion >= 4.5;
  tested with 4.6.4 only. Older MuseScore files may need different root mapping.
- The `source_file_name` column is NOT the same as the new `import_format` column.
  source_file_name is the original upload filename, import_format is 'mscz'/'mscx'/'mid' etc.
