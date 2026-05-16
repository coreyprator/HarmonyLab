# HarmonyLab prototype — live-data mode

This adds an **optional read-only live mode** to the existing redesign prototype so PL can validate against his real 42-song library before HM44 begins.

## TL;DR

1. Open `prototype.html` (mock mode is the default — nothing changes).
2. Click the **`● Mock`** pill in the floating prototype panel (bottom right).
3. Choose **Live · read-only**, paste a JWT from production, click **Go live**.
4. A red **`LIVE DATA · READ-ONLY`** banner appears across the top of every page.
5. Library and song detail now fetch from `https://harmonylab.rentyourcio.com`.
6. Any write you attempt shows a toast: *"Live mode is read-only · {METHOD} {path} · would write in HM44"*.
7. Click the pill again at any time to switch back to mock.

The mock-mode default is preserved. Same URL serves both modes.

## How to get a JWT

In another tab, open `https://harmonylab.rentyourcio.com` and sign in. Then in DevTools console of that tab:

```js
localStorage.getItem("harmonylab_token")
```

Copy the long `eyJ…` string and paste it into the prototype's JWT field.

The prototype stores it in **sessionStorage** (`hl_proto_jwt`), so it dies when you close the tab. The backend origin is stored in localStorage (`hl_proto_base`) so you can re-paste a token without re-entering the URL.

Tokens expire hourly. When that happens the prototype shows a "Paste a fresh JWT" error state with a button that re-opens the dialog.

## What goes live

Seven GET endpoints, exactly as the brief specified:

| Endpoint | Used by | Notes |
|---|---|---|
| `GET /api/v1/songs/` | Library page | Each row through `beSongToLibraryRow()` |
| `GET /api/v1/songs/{id}` | Song header + audit page | |
| `GET /api/v1/analysis/songs/{id}` | Score workbench | Provides chords/measures/sections payload |
| `GET /api/v1/analysis/songs/{id}/key-centers` | Key-center band on the staff | |
| `GET /api/v1/analysis/songs/{id}/exchanges` | Right-rail AI exchanges | |
| `GET /api/v1/analysis/songs/{id}/overrides` | Right-rail overrides | |
| `GET /api/v1/vocabulary/chord-symbols` | ChordPicker dropdown | Falls back to local fixture if BE response shape differs |

Live mode wraps every fetch with `Authorization: Bearer <token>` and `credentials: "omit"` (no cookie leakage). Requests sent to `${base}/api/v1/...` — base is configurable in the dialog.

## What stays mock (NEW-BE features)

Per the reconciliation matrix, these features depend on schema or endpoints that HM44 must add. They keep mock behaviour even in live mode and flag themselves visibly:

| Feature | Why mock | How it surfaces |
|---|---|---|
| Inferred chord visual | `Chords.is_inferred` column not added yet | Always renders prototype's example (Corcovado m.1–2). |
| Voicing notation in edit popover | `Chords.voicing_notation` column not added yet | Label gets a small "· mock" tag in live mode. |
| AI key-center **Accept** button | `KeyRegions` CRUD endpoints not added yet | Banner inside the AI dialog: "HM44 adds POST /analysis/{id}/key-regions". Accepting toasts only — no DB write. |
| Section banner click-to-rename | Section-rename endpoint not added yet | Plan only; not yet interactive. |

## Write paths in live mode

All write paths short-circuit at the call site. Each one calls `hlLiveToastFor(api, toast, "METHOD /path")` first. In mock mode the helper returns false and the write happens in local state; in live mode it returns true and a toast appears showing the endpoint that *would* be hit. No real PUT/POST/DELETE ever leaves the browser in live mode.

Covered writes:

- `PUT /chords/{id}` (chord edit popover Save) — also covers the secondary `PUT /analysis/songs/{id}/chord/{idx}` write.
- `PUT /chords/{id}` (inferred chord "accept ↩" promotion).
- `POST /analysis/songs/{id}/manual-key` (key-pill pencil → pick new key).
- `POST /analysis/songs/{id}` (Re-analyze).
- `POST /analysis/songs/{id}/exchanges/{eid}/outcome=reject` (AI dialog Reject).
- KeyRegion writes (AI dialog Accept) — flagged as NEW-BE inside the dialog itself.

## Hosting

The prototype is a static page (HTML + JSX + CSS, no build step). Drop the entire project folder into any static host:

- **Vercel** — `vercel deploy` from the project root. The site is `/prototype.html` at the deployed origin.
- **Netlify** — drag the folder onto the Netlify dashboard. Same URL pattern.
- **Cloudflare Pages** — connect a Git repo or use Direct Upload.
- **GitHub Pages** — push the folder to a `gh-pages` branch.

**CORS:** the BE must allow the prototype's origin. After deploying, send PL the origin URL (e.g. `https://harmonylab-proto.vercel.app`) and CC adds one line to FastAPI:

```py
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://harmonylab-proto.vercel.app"],   # add this
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Once that ships, the prototype's live mode works against production. Reverse it after validation.

## Files added in this iteration

| File | Purpose |
|---|---|
| `proto/api.jsx` | API client + `ApiProvider` + `useSong/useLibraryRows/useChordVocabulary` hooks + BE→prototype transforms. |
| `proto/live-ui.jsx` | `LiveBanner`, `ModeToggle`, `ModeDialog`, `LoadingState`, `ErrorState`. |
| `proto/app.jsx` | Wrapped in `ApiProvider`; routes through hooks; `LoadingShell` for in-flight states. |
| `proto/views.jsx` | `Library` switched to `useLibraryRows()` with loading/error states. |
| `proto/song.jsx` | `SongDetail` accepts `onOpenMode`; write paths short-circuit via `hlLiveToastFor`. |
| `proto/components.jsx` | `ChordEditPopover` shows "· mock" on the voicing field in live mode; `AIKeyCenterDialog` shows a NEW-BE warning banner. |
| `prototype.html` | Loads `api.jsx` and `live-ui.jsx` before `components.jsx`. |
| `LIVE_MODE_README.md` | **This document.** |

## Validation playbook for PL

Once CORS is allowlisted:

1. Open the hosted prototype URL.
2. Switch to live mode, paste your token.
3. **Library:** every column should sort + filter against your 42 real songs. Check the Data column — confirm row counts for `XML`, `NOTES`, `LYRICS`, override counts match what you expect.
4. **Each song detail:** scroll the score workbench. Watch for:
   - Chord symbols cropping into adjacent measures (system-break threshold may need tuning).
   - Key-center band misalignment with the chord row.
   - Roman numerals splitting `superscript` wrong (the prototype regex assumes patterns like `V7♭9` — long-tail symbols may break).
   - Synthetic staff layout for songs without `raw_xml` (should hit ~32 of 42).
5. Try the multi-select + Identify-key-center flow on a real cadence. Accept toast should appear with the KeyRegion-write endpoint that HM44 needs to add.
6. Try chord edit on a low-confidence chord. Save toast confirms which PUT would fire.
7. Send findings to PL. Visual issues + layout regressions feed final pre-HM44 corrections; data-shape mismatches feed BE response-shape requirements for HM44.

## Reverting

In the prototype: click the pill → **Reset to mock**. Wipes the JWT from sessionStorage, flips mode back to mock, reloads to the local fixtures.

On the backend: CC removes the CORS allowlist entry. Reversible in one commit.
