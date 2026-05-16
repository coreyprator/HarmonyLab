# HarmonyLab Redesign — Reconciliation Report

**Author:** Claude Design (CD)
**Date:** 2026-05-16
**For:** PL → CAI → HM44 sprint planning
**Sources:** `HL_FEATURE_INVENTORY.md` (82 routes, 30 tables) · `index.html` (spec doc) · `prototype.html` (interactive)

This document reconciles every visible element in the redesign against the live
backend inventory, and lists the discrete BE changes CAI needs to make for HM44.
It is the authoritative addendum to the rationale in `index.html`; both have been
updated together.

---

## Part 1 — What changed since the original spec

The original spec doc (delivered May 15) used a four-tab Song page (Chords /
Analysis / Notation / Notes). It went through six rounds of review with PL +
teammates. The current design differs in these material ways:

| # | Change | Rationale |
|---|---|---|
| 1 | **Tabs merged into one score workbench.** No more Chords / Analysis / Notation / Notes. Notation, chord symbols, roman numerals, function labels, lyrics live on one page in MuseScore-style chord-above-staff layout. | "All four need to be on a score to be useful." — PL. The cells below the notation were redundant with the chord symbols above; collapsing reclaims a full screen of vertical space and removes a context-switch tax. |
| 2 | **Auto system-break by chord density.** Long chord symbols force fewer measures per system; section boundaries always break. | Prevents chord-symbol collision in dense bars (e.g. `F♯m7♭5/G♭` in m.7 of Corcovado). Threshold: ≤4 chars/8 bars, ≤6 chars/6 bars, longer/4 bars. |
| 3 | **Multi-select + AI key-center identification.** ⌘-click / shift-click chord symbols, then **✦ Identify key center** sends the selection to Claude. Suggestion comes back with confidence, pattern, and reasoning; accept inserts a `KeyRegion` and re-tints the affected chord cells; reject logs an exchange. | The original design only let users set a song-level key. Real jazz has modulation; a per-region affordance was needed. Reuses existing `POST /analysis/songs/{id}/ai-analysis` + `outcome` endpoints. |
| 4 | **Right-rail Study Notes drawer** replaces the Notes tab. Three sub-tabs: Comments, AI exchanges, Overrides. Click any item to jump to the chord. | The score workbench needs to retain access to comment/exchange data without a top-level tab. Drawer is dismissible; closes on its own button. |
| 5 | **Chord-symbol picker is a vocabulary dropdown**, not free-text. Filterable by symbol or quality alias. | Per Corey's review. Surfaces `GET /api/v1/vocabulary/chord-symbols` (BE existed; no FE caller). |
| 6 | **Library grid: per-column sort + multi-select filter.** Every column has ▲▼ for sort and a ▼ for multi-select filtering with row counts. | Per Corey's review. Replaces the single genre dropdown + title text-filter. Footer summarises active filters + sort. |
| 7 | **Library has a Genre column.** | Per Corey's review. Joins to `Songs.genre` (already in DB). |
| 8 | **Lab feature verdicts: REVIVE for AI Improvisation + RLHF sessions** (not deprecate, as originally proposed). | PL: low usage to date reflects AI context plumbing limitations, not wrong-fit features. Keep available in `/lab` for HM45+ once context engineering matures. |

The IA diagram, design tokens, component library, settings page, audit page,
import modal, and theory chat drawer are unchanged from the original spec; the
reconciliation rows for those elements still apply as written.

---

## Part 2 — Reconciliation matrix

**Status legend:**
- `EXISTING` — BE endpoint(s) + schema column(s) are present today and used by the redesign as-is.
- `SCHEMA-READY` — DB column exists with 0 reads/writes today; redesign adds the read/write path. No schema change.
- `NEW-BE` — requires a new endpoint, response shape, or column. CAI must fold into HM44 (or defer with note).
- `FREE-WIN` — endpoint already exists but no FE caller today; redesign adds the FE call site.

### A — Library page

| Mockup element | What it does | Endpoint(s) | Schema | Status | Notes |
|---|---|---|---|---|---|
| Song list table | Renders all songs with title/composer/genre/key/form/measures/chords/imported/source-modified/data flags | `GET /songs/` | `Songs`, `song_imports` | NEW-BE | **REQ-017**: `song_imports.fs_modified_at` exists but list endpoint does not JOIN. Expand `/songs/` response. |
| Genre column | Per teammate review (added 2026-05-16) | `GET /songs/` | `Songs.genre` | EXISTING | Column already in DB; just include in response if not already. |
| Per-column sort | ▲▼ on every header column | `GET /songs/?sort=col&dir=asc` | n/a | NEW-BE | Add `sort`, `dir` query params; client-side fallback acceptable for 42 rows. |
| Per-column multi-select filter | ▼ on text/categorical columns; multi-value selection with row counts | `GET /songs/?filter[col]=v1,v2` | n/a | NEW-BE | Add per-column filter query params. For 42 rows, client-side filter is also acceptable. |
| Data column badges (XML · NOTES · LYRICS · overrides) | Boolean capability badges per song | `GET /songs/` | `Songs.has_note_data`, `has_lyrics`, `raw_xml`, `ChordAnalysisOverrides` | NEW-BE | Expose `has_raw_xml` boolean in response; count `overrides` via JOIN or denorm column. |
| Bulk delete | Cascade-delete 1+ selected songs | `DELETE /songs/bulk/delete` | `Songs` + 14 child | EXISTING | Working today. |
| Import drawer · Score / OMR / Batch | Drop file, preview, edit before commit | `POST /imports/{score|omr|batch}/{preview\|import}` | `Songs`, `Sections`, `Measures`, `Chords`, `song_notes`, `song_lyrics`, `song_imports`, `Songs.raw_xml` | EXISTING | BUG-024 (OMR 504 timeout) assumed fixed in HM43. |
| Inline-edit preview chords before commit | User corrects low-confidence chords in the preview grid before pressing Import | local state → `/{omr\|score}/import` body | n/a in-flight | NEW-BE | Today the import endpoint takes server-parsed payload; extend body to accept client-edited `chords[]`. |

### B — Song detail (Score Workbench)

| Mockup element | What it does | Endpoint(s) | Schema | Status | Notes |
|---|---|---|---|---|---|
| Notation pane (OSMD) on every song | Renders MusicXML staff above each system's chord row | `GET /songs/{id}` with raw_xml in response | `Songs.raw_xml` | NEW-BE | raw_xml stored but never returned to FE. Add to `/songs/{id}` response (or new `/songs/{id}/xml`). |
| Synthetic staff fallback | When `raw_xml` is missing, render bar-lines + measure numbers; chord interactions still work | `GET /songs/{id}` | reads `Songs.raw_xml IS NULL` | EXISTING | Pure FE behavior over existing data. |
| Section banner (A1, A2, B, A3) above first system of each section | Section name + subtitle + measure range; click-to-rename (planned) | `PATCH /sections/{id}` (today) or `Songs.section_markers_json` | `Sections.name`, `Songs.section_markers_json` | SCHEMA-READY | Recommend writing to `Sections.name`; `section_markers_json` available for form-level overrides. |
| Key-center band (tinted per-measure) | Segmented underscore showing each measure's active key center | `GET /analysis/songs/{id}/key-centers` | `KeyRegions` | EXISTING | Working today; only 1 row populated. Inference algorithm populates more. |
| Chord symbol — click to edit | Primary edit surface | `PUT /chords/{id}` and/or `PUT /analysis/songs/{id}/chord/{idx}` | `Chords.chord_symbol`, `chord_symbol_override`, `ChordAnalysisOverrides` | EXISTING | **chord_index FK migration** required before override-by-index is safe (per brief Part 4). |
| ChordPicker dropdown (canonical vocabulary) | Searchable dropdown listing root × quality combinations | `GET /api/v1/vocabulary/chord-symbols` | `ChordVocabulary` (30 rows) | FREE-WIN | BE exists; no FE caller today. Prototype demonstrates the call site. |
| Roman numeral row below staff | Italic small-caps Roman analysis per chord | `GET /analysis/songs/{id}` | `Chords.roman_numeral`, `ChordAnalysisOverrides.roman_override` | EXISTING | Override path same as symbol. |
| Function-label row | Tonic / dominant / secondary-V / etc. | `GET /analysis/songs/{id}` | `Chords.function_label`, `function_override` | EXISTING | |
| Voicing notation (below chord symbol) | New: "rootless A", "drop-2", "shell 3-7-9" | `PUT /chords/{id}` | `Chords` · **new column** `voicing_notation` | NEW-BE | Add `voicing_notation NVARCHAR(50)`. Brief §3 REQ-2. |
| Comment dot (orange) above chord | Per-chord free-text comment | `PUT /chords/{id}` | `Chords.comments` (0 rows used) | SCHEMA-READY | Column exists; PUT body already supports it. |
| Inferred chord visual | Italic + dotted underline + 60% opacity + leading `·` | `GET /analysis/songs/{id}` | `Chords` · **new column** `is_inferred` | NEW-BE | Add `is_inferred BIT DEFAULT 0`. Distinct from BUG-007 fill-forward (which must still be disabled). |
| "Accept ↩" promotion of inferred | Promotes inferred chord to composer-written; clears `is_inferred` | `PUT /chords/{id}` | sets `is_inferred=0, is_manual_edit=1` | SCHEMA-READY | Uses existing flags once `is_inferred` lands. |
| Multi-select chord toolbar | ⌘-click / shift-click → sticky toolbar with selection summary + actions | local state | n/a | NEW-BE | Pure FE; no BE work. |
| **✦ Identify key center** (AI) | Submits selected chords to Claude; returns suggestion + reasoning + confidence | `POST /analysis/songs/{id}/ai-analysis` with `selected_chords=[]` | `HarmonicAnalysisExchanges` write | EXISTING | Body already accepts `selected_measures/selected_chords` (comma-delimited). |
| Accept AI suggestion → KeyRegion write | Creates a user-defined KeyRegion for the selection's measure range | NEW `POST /analysis/songs/{id}/key-regions` | `KeyRegions` (`is_user_defined`) | NEW-BE | Column exists; endpoints don't. ~4 routes (POST/PUT/DELETE + bulk merge). |
| Accept/reject log | Records outcome of AI suggestion | `POST /analysis/songs/{id}/exchanges/{eid}/outcome` | `HarmonicAnalysisExchanges.outcome`, `rejection_reason` | EXISTING | |
| Key pill + manual override pencil | Set/clear song-level key | `POST /analysis/songs/{id}/manual-key` | `SongAnalysis.manual_key_override` | EXISTING | |
| Re-analyze button | Force recompute (preserves overrides) | `POST /analysis/songs/{id}` | `SongAnalysis` cache | EXISTING | |
| Right-rail · Comments | List of all commented chords, click-to-jump | `GET /analysis/songs/{id}` (chord comments inline) | `Chords.comments` | SCHEMA-READY | |
| Right-rail · AI exchanges | History of theory-chat + key-center identifications | `GET /analysis/songs/{id}/exchanges` | `HarmonicAnalysisExchanges` | EXISTING | |
| Right-rail · Overrides | List of all manually-edited chords | `GET /analysis/songs/{id}/overrides` | `ChordAnalysisOverrides` | EXISTING | Route exists; no FE caller today → FREE-WIN. |
| Bottom analysis row (timeline + patterns + phrases) | Three cards: full-song key timeline, detected patterns, detected phrases | `GET /analysis/songs/{id}/{key-centers,patterns,phrases}` | `Chords`, `JazzTheoryPatterns`, `KeyRegions` | EXISTING | |
| Theory chat drawer | Conversational Q&A scoped to selected chords | `POST /analysis/theory-chat`, `POST /analysis/songs/{id}/ai-analysis` | `HarmonicAnalysisExchanges`, `jazz_theory_docs`, `analysis_rules` | EXISTING | 50 rows real usage. |
| Export menu (`.mscz` · `.musicxml` · PDF) | Round-trip edited score | `GET /exports/musescore/{id}` + new `/exports/musicxml/{id}` | `Songs`, `Chords`, `Measures` | NEW-BE | MuseScore endpoint exists (FREE-WIN wiring); MusicXML endpoint is new. |

### C — Settings page

| Mockup element | What it does | Endpoint(s) | Schema | Status | Notes |
|---|---|---|---|---|---|
| Chord notation seg (Jazz · Plain) | Δ ø ° vs maj/m/dim | `GET/PUT /preferences` | `UserPreferences.chord_symbol_mode` | EXISTING | |
| Key-center color pickers ×24 | User picks per-key colors; live-applied to chord cells | `GET/PUT /preferences` | `UserPreferences.key_center_colors` (JSON dict) | EXISTING | |
| Voicing-notation defaults | User-set default voicing labels | `PUT /preferences` | `UserPreferences` · **new column** `default_voicing_notation` | NEW-BE | Optional. Only useful once `Chords.voicing_notation` lands. |
| Debug mode toggle | Enables HLDebug overlay | `GET/PUT /preferences` | `UserPreferences.debug_mode` | EXISTING | |

### D — Audit page

| Mockup element | What it does | Endpoint(s) | Schema | Status | Notes |
|---|---|---|---|---|---|
| Audit page | Per-song notes/lyrics/dynamics/tempo/time/key marks, import history, diagnostics | `GET /songs/{id}/audit`, `GET /songs/{id}/imports` | `song_notes`, `song_lyrics`, `song_imports`, `song_tempos`, etc. | EXISTING | Working. Audit cookie-auth mismatch noted in inventory §E.4 (out of scope). |
| Reparse notes button | Re-extract notes from stored `raw_xml` | `POST /imports/score/reparse-notes` | `song_notes`, reads `Songs.raw_xml` | EXISTING | |

### E — Lab page (deemphasized stubs)

| Feature | Verdict | Status | Notes |
|---|---|---|---|
| Riffs library | KEEP in /lab | EXISTING | `GET /riffs/` · 10 hardcoded · low maintenance. |
| Quiz | RETRY in /lab | EXISTING (stub) | Move from top-level; surface "Quiz me on this song" on song detail. 0 attempts ever — possibly entry friction. |
| Progress tracking | RETRY in /lab | EXISTING (stub) | Reduce to per-song last-practiced + 5-pt mastery; surface on song detail. 0 rows ever. |
| **AI Improvisation** | **REVIVE in /lab** (was: deprecate) | EXISTING (stub) | Per PL: 0 sessions reflect AI context plumbing limits, not wrong fit. Keep wired; revisit once context engineering matures. |
| **RLHF sessions** | **REVIVE in /lab** (was: deprecate) | EXISTING (stub) | Per PL: same reasoning. Held pending higher-quality AI suggestions. Per-chord edits + theory-chat outcomes still cover single-shot RLHF independently. |
| WebMIDI input | WIRE | EXISTING (no FE) | `GET /midi/webmidi-check` available; could power live chord identification at the piano. |

---

## Part 3 — New BE work, ordered by dependency

**Critical path for HM44** (the redesign cannot ship without these):

1. **FK migration on `ChordAnalysisOverrides`** — replace positional `chord_index` with `chord_id` FK. Per brief Part 4; blocks all inline editing.
2. **Disable BUG-007 fill-forward** in `analysis_service.py`. Required before OSMD ships or wrong chords render over empty measures.
3. **Surface `Songs.raw_xml`** in `GET /songs/{id}` (or new `GET /songs/{id}/xml`). OSMD needs MusicXML. Verify all import paths capture raw_xml.
4. **Add `Chords.is_inferred BIT`** column + populate from chord-inference algorithm (TBD). Distinct from fill-forward.
5. **Add `Chords.voicing_notation NVARCHAR(50)`** + extend `PUT /chords/{id}` body to accept it. Brief §3 REQ-2.
6. **Add MusicXML export**: `GET /exports/musicxml/{song_id}`. Mirror existing MuseScore export.
7. **Expand `GET /songs/` response** with `fs_modified_at` (REQ-017 JOIN to `song_imports`), `has_raw_xml`, `override_count`. Add `sort` + `filter[col]` query params (or accept client-side filter for 42 rows).
8. **KeyRegions CRUD**: `POST/PUT/DELETE /analysis/songs/{id}/key-regions[/{id}]`. ~4 routes. Required for the AI key-center accept flow.

**Free wins** (BE exists, just wire the FE):

- Export menu `.mscz` button → `GET /exports/musescore/{id}`.
- ChordPicker dropdown → `GET /vocabulary/chord-symbols`.
- Per-chord CRUD on the edit popover → `PUT/DELETE /chords/{id}`.
- Chord comments storage → `Chords.comments` (column exists; 0 rows).
- Right-rail overrides list → `GET /analysis/songs/{id}/overrides`.
- WebMIDI status pill → `GET /midi/webmidi-check`.

**Deferrable** (would be nice; not blocking):

- `UserPreferences.default_voicing_notation` (only useful after voicing_notation column lands).
- KeyRegions drag-to-resize UI (the AI accept path covers the main use case).

---

## Part 4 — Risks + open questions

1. **chord_index drift before FK migration.** If a chord is inserted/deleted between two saves of the same override, indices shift and overrides break. CAI must do the FK migration **before** any user-facing inline editing ships. The prototype assumes `chord_id` semantics throughout.

2. **raw_xml coverage gap (32/42 songs).** The graceful "synthetic staff" fallback works, but the user will reach for re-import for most songs. Verify HM44 import pipeline guarantees raw_xml capture, then propose a one-time backfill (re-run the parsers over the existing `source_file_name`s if they're still on disk).

3. **Chord inference algorithm not specified.** REQ-018 says "inferred chord" but doesn't fix an algorithm. The prototype renders the visual treatment; the algorithm itself is a separate decision. Recommend: smallest viable rule (analyse the melody notes in the empty measure; pick the dominant chord whose pitches contain those notes), iterate based on user accept/reject rate on the inferred-chord "accept ↩" button.

4. **AI key-center identification reuses ai-analysis endpoint.** The existing `POST /analysis/songs/{id}/ai-analysis` accepts `selected_measures` + `selected_chords` (comma-delimited strings). The redesign's AI dialog uses it for both general theory questions and key-center identification — distinguished only by the prompt scaffolding. Acceptable today; CAI may want a dedicated `POST /analysis/songs/{id}/key-center-suggest` if the prompts diverge significantly.

5. **Lab features deferred, not deleted.** Per PL: AI Improvisation + RLHF sessions stay code-resident. The redesign deemphasises them (one click off the top nav) but does not remove them. CAI: leave Python routes alive even if the FE rarely hits them.

6. **Sort + filter on `GET /songs/`.** For 42 rows, client-side sort/filter is fine; the prototype demonstrates that. If the library grows past ~500, move to server-side. The matrix flags this as NEW-BE for completeness.

7. **iPad target.** The score workbench was tested at 1280px. iPad-min landscape (1180px) compresses the chord row but stays readable; portrait drops below the 4-system threshold and triggers more frequent system breaks. Verify with PL on hardware.

---

## Part 5 — Files in this package

| File | Purpose |
|---|---|
| `index.html` | Spec doc — IA, design tokens, component library, all mockups, rationale, original matrix. Read top-to-bottom. |
| `prototype.html` | **Interactive prototype.** Open this to test-drive the redesign. Hash routing: `#/song/12` for Corcovado (full notation), `#/song/4` for All The Things You Are (synthetic staff). |
| `redesign.css` | All design tokens + component CSS. Imported by both `index.html` and `prototype.html`. |
| `proto/data.jsx` | Mock data: 5 hand-curated songs + 12 library-only rows. Mirrors live schema shape. |
| `proto/components.jsx` | Shared React components: Toast, ChordCell, ChordPicker, ChordEditPopover, KeyPopover, Topbar, ConfirmModal, AIKeyCenterDialog. |
| `proto/views.jsx` | Library, Settings, Audit, Lab, Import modal. |
| `proto/song.jsx` | Song detail page (the workbench host). Wires the score component + drawers + popovers. |
| `proto/score.jsx` | Score workbench: system grouping, key-center band, chord symbol row, staff/synthetic staff, RN row, function row, right rail, bottom analysis. |
| `proto/app.jsx` | Top-level App + hash router. Mounts to `#root`. |
| `RECONCILIATION.md` | **This document.** |
| `uploads/HL_FEATURE_INVENTORY.md` | Source-of-truth inventory (provided by PL). |

---

*End of report. Send to CAI with the package. Reply to PL with any matrix rows that need clarification before sprint planning.*
