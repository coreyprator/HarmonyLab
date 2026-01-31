# HarmonyLab Project Status

**Last Updated**: 2025-01-28
**Project Lead**: Corey
**Production URL**: https://harmonylab.rentyourcio.com
**Repository**: GitHub (private)
**Methodology**: coreyprator/project-methodology v3.5

---

## 1. Current Sprint/Phase

### Sprint 1: COMPLETE ✅

**Sprint 2: Frontend Development → READY TO START**

All backend infrastructure, API endpoints, and MIDI parsing are deployed and working. The project is ready to begin frontend development.

---

## 2. What's Working (Deployed & Tested)

### Infrastructure ✅

| Component | Status | Details |
|-----------|--------|---------|
| Cloud Run | ✅ Live | `harmonylab` service in us-central1 |
| Custom Domain | ✅ Configured | harmonylab.rentyourcio.com |
| Cloud SQL | ✅ Connected | `HarmonyLab` database on `flashcards-db` instance |
| Secret Manager | ✅ Configured | 4 secrets (db-server, db-name, db-user, db-password) |
| GitHub Actions | ✅ Working | Workload Identity Federation, auto-deploy on push |
| Health Check | ✅ Passing | `/health` endpoint returns OK |

### Backend API ✅

**36 endpoints operational** across these categories:

| Category | Endpoints | Status |
|----------|-----------|--------|
| Health | `/health` | ✅ |
| Songs | CRUD operations | ✅ |
| Sections | CRUD operations | ✅ |
| Measures | CRUD operations | ✅ |
| Chords | CRUD operations | ✅ |
| Vocabulary | Chord types, roman numerals | ✅ |
| Quiz | Generate, submit, history | ✅ |
| Progress | Stats, tracking | ✅ |
| Imports | MIDI upload, audit, preview | ✅ |

**API Docs**: https://harmonylab.rentyourcio.com/docs

### MIDI Parser ✅

| Item | Status | Commit |
|------|--------|--------|
| Multi-track parsing | ✅ Fixed | `6baf637` |
| Chord detection | ✅ Working | 45/48 chords detected in test file |
| Confidence scoring | ✅ Working | Returns 0-100% confidence per chord |
| Audit report | ✅ Working | Clean UI showing progression |
| Shell voicing recognition | ✅ Working | Detects jazz left-hand voicings |

**Verified by Corey**: 2025-01-07

### Database Schema ✅

9 tables implemented:
- `Songs`, `Sections`, `Measures`, `Chords`
- `ChordTypes`, `RomanNumerals` (vocabulary)
- `QuizAttempts`, `QuizAnswers`
- `Progress`

### Documentation ✅

| Document | Purpose | Status |
|----------|---------|--------|
| `UI_DESIGN.md` | Frontend specifications, wireframes, components | ✅ Complete |
| `TEST_PLAN.md` | 80+ test cases, coverage requirements | ✅ Complete |
| `USER_GUIDE.md` | End-user documentation | ✅ Complete |
| `SPRINT2-HANDOFF.md` | VS Code AI instructions | ✅ Complete |

### Assets ✅

| Asset | Status |
|-------|--------|
| Favicon set | ✅ Generated (ico, png, apple-touch, PWA icons) |
| site.webmanifest | ✅ Created |

---

## 3. What's In Progress or Broken

### In Progress 🟡

| Item | Status | Notes |
|------|--------|-------|
| Frontend (React) | Not started | Designed in UI_DESIGN.md, ready to build |
| Automated tests | Not started | TEST_PLAN.md complete, 0% coverage currently |
| Song library data | Empty | Parser works, need to import songs |

### Known Issues 🔴

| Issue | Severity | Description | Fix Available |
|-------|----------|-------------|---------------|
| **Chord voicing playback** | Medium | Tone.js plays simple triads instead of full chord tones (e.g., Am6 plays A-C-E instead of A-C-E-F#) | ✅ Yes - `VSCODE-FIX-CHORD-VOICINGS.md` |
| **Parser includes melody notes** | Low | Some chords have low confidence because melody notes get combined with harmony (e.g., measure 4 of Corcovado shows "Ab" instead of "Abdim7") | ✅ Yes - Manual chord editing feature needed |
| **No manual chord editing** | Medium | Users cannot correct parser mistakes in the UI | ✅ Yes - `VSCODE-FEATURE-CHORD-EDITING.md` |

### Pending Features (Sprint 2)

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| React + Vite + Tailwind setup | P0 | 1-2h | Project initialization |
| Song Library (Home) | P0 | 2-3h | Browse, search, filter songs |
| Song Detail + Chord Grid | P0 | 3-4h | View chord progressions |
| Tone.js Audio Playback | P1 | 3-4h | Hear chord progressions |
| Quiz Interface | P1 | 4-6h | Practice chord recall |
| Progress Dashboard | P2 | 2-3h | Track learning progress |
| MIDI Import UI | P2 | 2-3h | Upload new songs |
| **Manual Chord Editing** | P1 | 3-4h | Fix parser mistakes |
| **Chord Inversions/Octave** | P2 | 2h | Control playback voicings |

---

## 4. Key Decisions Made

### Architecture Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| **Cloud-first (no localhost)** | Per methodology v3.5 — all testing against Cloud Run URL, no .env files | Sprint 1 |
| **Cloud SQL with SQL Server** | Shared instance with Super-Flashcards project (`flashcards-db`) | Sprint 1 |
| **FastAPI backend** | Async support, automatic OpenAPI docs, Python ecosystem | Sprint 1 |
| **React + Vite + Tailwind** | Modern tooling, fast builds, utility-first CSS | Sprint 1 |
| **Tone.js for audio** | Best-in-class Web Audio library, piano samples available | Sprint 1 |

### MIDI Parser Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| **Combine ALL tracks** | Jazz piano has melody + harmony in separate tracks; single-track analysis missed chord voicings | 2025-01-28 |
| **30-tick chord window** | Notes within 30 ticks (~1/16 beat at 480 TPB) are considered simultaneous | 2025-01-28 |
| **Shell voicing recognition** | Jazz uses root + 3rd + 7th without 5th; parser must recognize these as valid chords | 2025-01-28 |
| **Confidence scoring** | Parser returns 0-100% confidence; UI flags <50% for manual review | 2025-01-28 |
| **Manual override capability** | Parser can't be perfect; users need ability to correct chord symbols | 2025-01-28 |

### Testing Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| **70% coverage minimum** | Enforced in CI/CD; deployment fails if not met | Sprint 1 |
| **Test against Cloud Run** | No localhost testing per methodology | Sprint 1 |
| **Write tests with features** | Not after; prevents untested code from shipping | Sprint 1 |

---

## 5. Technical Debt & Known Issues

### Technical Debt

| Item | Impact | Effort to Fix | Priority |
|------|--------|---------------|----------|
| **0% test coverage** | High risk for regressions | 8-12 hours | HIGH |
| **No error boundaries in frontend** | Crashes show blank screen | 1-2 hours | Medium |
| **Chord voicing function incomplete** | Playback sounds wrong | 2 hours | HIGH |
| **No manual chord editing** | Can't fix parser mistakes | 3-4 hours | HIGH |
| **No database migrations** | Schema changes require manual SQL | 2-3 hours | Low |

---

## 6. Project Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| API Endpoints | 36 | 36 | ✅ Complete |
| MIDI Parser | Working | Working | ✅ Complete |
| Code Coverage | 0% | 70% | 🔴 Not started |
| Frontend Pages | 0 | 5+ | 🔴 Not started |
| Songs in Database | 0 | 37 | 🟡 Parser ready |
| Custom Domain | ✅ | ✅ | ✅ Complete |

---

## 7. Reference Links

| Resource | URL |
|----------|-----|
| Production | https://harmonylab.rentyourcio.com |
| API Docs | https://harmonylab.rentyourcio.com/docs |
| Health Check | https://harmonylab.rentyourcio.com/health |

---

**Document Version**: 3.0
**Status**: Ready for Sprint 2
