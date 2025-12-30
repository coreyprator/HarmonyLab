# HarmonyLab Sprint 2 Handoff: Frontend Implementation

**Date**: 2025-12-28  
**From**: Claude (Architect)  
**To**: VS Code AI (Coder)  
**Status**: Sprint 1 Deliverables Complete ✓

---

## Sprint 1 Deliverables (Ready for Implementation)

| Document | Purpose | Location |
|----------|---------|----------|
| **UI_DESIGN.md** | Visual specs, components, file structure | `docs/UI_DESIGN.md` |
| **TEST_PLAN.md** | All test cases, coverage requirements | `docs/TEST_PLAN.md` |
| **USER_GUIDE.md** | End-user documentation (source of truth) | `docs/USER_GUIDE.md` |

**Methodology Reference**: `G:\My Drive\Code\Python\Harmony-Lab\project-methodology-main\`

---

## Backend Status ✅

The backend is deployed and operational:

| Resource | URL |
|----------|-----|
| **API Base** | https://harmonylab-wmrla7fhwa-uc.a.run.app |
| **API Docs** | https://harmonylab-wmrla7fhwa-uc.a.run.app/docs |
| **Health Check** | https://harmonylab-wmrla7fhwa-uc.a.run.app/health |

**36 endpoints available** — See API docs for full list.

---

## Your Tasks (Sprint 2)

### Phase 1: Project Setup

```powershell
# Navigate to project
cd "G:\My Drive\Code\Python\Harmony-Lab"

# Create frontend directory
mkdir frontend
cd frontend

# Initialize Vite + React
npm create vite@latest . -- --template react

# Install dependencies
npm install
npm install -D tailwindcss postcss autoprefixer
npm install react-router-dom tone

# Initialize Tailwind
npx tailwindcss init -p

# Create environment file
echo "VITE_API_URL=https://harmonylab-wmrla7fhwa-uc.a.run.app" > .env
```

### Phase 2: Implement Components

**Build order (matches UI_DESIGN.md):**

1. **Layout** — Header, navigation
2. **Song Library** — Home page with search/filter
3. **Song Detail** — Chord grid, metadata
4. **Playback** — Tone.js integration
5. **Quiz** — Setup, interface, results
6. **Progress** — Dashboard, stats
7. **Import** — File upload, preview

### Phase 3: Implement Tests

**Test order (matches TEST_PLAN.md):**

1. **API tests** — All endpoint tests
2. **Component tests** — Each UI component
3. **Integration tests** — Full workflows
4. **Playback tests** — Tone.js functionality

### Phase 4: CI/CD Integration

Update `.github/workflows/deploy.yml` to:
1. Run tests before deploy
2. Enforce 70% coverage
3. Build frontend
4. Deploy to Cloud Run

---

## Key Implementation Notes

### API Client

```javascript
// src/api/client.js
const API_URL = import.meta.env.VITE_API_URL;

export async function apiClient(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }
  return response.json();
}
```

### Chord Grid Component

Per UI_DESIGN.md:
- 4 measures per row
- Yellow highlight during playback
- "?" for blank cells in quiz mode
- Click to play single chord

### Tone.js Setup

```javascript
// src/context/AudioContext.jsx
import * as Tone from 'tone';

const piano = new Tone.Sampler({
  urls: { C4: "C4.mp3", /* ... */ },
  baseUrl: "https://tonejs.github.io/audio/salamander/",
}).toDestination();
```

### Error Messages

Per TEST_PLAN.md — all errors must be user-friendly:

```javascript
// ✅ GOOD
catch (error) {
  setError("Song not found. It may have been deleted.");
}

// ❌ BAD
catch (error) {
  setError(error.message); // May expose technical details
}
```

---

## File Structure to Create

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── api/
│   │   └── client.js
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx
│   │   │   └── Layout.jsx
│   │   ├── songs/
│   │   │   ├── SongList.jsx
│   │   │   ├── SongCard.jsx
│   │   │   └── SongDetail.jsx
│   │   ├── chords/
│   │   │   ├── ChordGrid.jsx
│   │   │   ├── ChordCell.jsx
│   │   │   └── ChordPicker.jsx
│   │   ├── quiz/
│   │   │   ├── QuizSetup.jsx
│   │   │   ├── QuizInterface.jsx
│   │   │   └── QuizResults.jsx
│   │   ├── playback/
│   │   │   ├── PlaybackControls.jsx
│   │   │   └── TonePlayer.js
│   │   ├── import/
│   │   │   ├── FileDropZone.jsx
│   │   │   └── ImportPreview.jsx
│   │   └── progress/
│   │       ├── StatsCards.jsx
│   │       └── MasteryTiers.jsx
│   ├── pages/
│   │   ├── HomePage.jsx
│   │   ├── SongPage.jsx
│   │   ├── QuizPage.jsx
│   │   ├── ProgressPage.jsx
│   │   └── ImportPage.jsx
│   ├── hooks/
│   │   ├── useSongs.js
│   │   ├── useQuiz.js
│   │   └── usePlayback.js
│   ├── context/
│   │   └── AudioContext.jsx
│   └── styles/
│       └── index.css
├── package.json
├── vite.config.js
├── tailwind.config.js
└── .env
```

---

## Definition of Done (Sprint 2)

### Testing ✓
- [ ] All API endpoint tests passing
- [ ] All component tests passing
- [ ] Integration tests passing
- [ ] Coverage ≥ 70%
- [ ] CI/CD runs tests before deploy

### UI ✓
- [ ] All pages render without errors
- [ ] Responsive on mobile and desktop
- [ ] Chord grid displays correctly
- [ ] Playback works with Tone.js
- [ ] Quiz flow complete
- [ ] Import flow complete
- [ ] Progress page shows data

### Documentation ✓
- [ ] Help link in header → USER_GUIDE.md on GitHub
- [ ] No console errors in production

### Deployment ✓
- [ ] Frontend builds successfully
- [ ] Deployed to Cloud Run
- [ ] All features work on production URL

---

## Constraints (DO NOT)

Per methodology v3.5:

- ❌ DO NOT upgrade Python beyond 3.12
- ❌ DO NOT change database schema without Claude approval
- ❌ DO NOT create new API endpoints without Claude design
- ❌ DO NOT test on localhost — use Cloud Run URL
- ❌ DO NOT skip tests — 70% coverage enforced

---

## Escalate to Claude When

- Architecture questions arise
- Database schema changes needed
- New API endpoints required
- Performance or security concerns
- Design-level bugs that need rethinking

---

## Quick Reference

### API Endpoints (Most Used)

```
GET  /api/songs                    # List all songs
GET  /api/songs/{id}               # Get song details
GET  /api/songs/{id}/progression   # Get full chord progression
GET  /api/vocabulary/chords        # Get chord dropdown options
POST /api/quiz/generate/{song_id}  # Generate quiz
POST /api/quiz/submit              # Submit quiz answers
GET  /api/progress                 # Get user progress
GET  /api/progress/stats           # Get aggregate stats
POST /api/imports/midi             # Upload MIDI file
```

### Design Tokens

```css
--color-primary: #2563eb;      /* Blue */
--color-success: #22c55e;      /* Green - correct */
--color-error: #ef4444;        /* Red - wrong */
--color-highlight: #fef08a;    /* Yellow - current chord */
--font-mono: 'JetBrains Mono'; /* Chord symbols */
```

---

## Start Here

1. Read `docs/UI_DESIGN.md` for visual specifications
2. Read `docs/TEST_PLAN.md` for test requirements
3. Read `docs/USER_GUIDE.md` for feature descriptions
4. Set up the frontend project structure
5. Implement components in the order specified above
6. Write tests as you build each component
7. Verify 70% coverage before marking complete

---

**Document Version**: 1.0  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5  
**Backend**: https://harmonylab-wmrla7fhwa-uc.a.run.app
