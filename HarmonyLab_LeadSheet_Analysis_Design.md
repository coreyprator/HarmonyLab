# 🔵 HarmonyLab — Lead Sheet Analysis Feature

**Version**: 1.2.2 → 1.3.0 (Phase 1) → 1.4.0 (Phase 2)  
**Date**: 2026-02-03  
**Status**: Design Complete — Ready for CC

---

## Overview

Transform HarmonyLab from a chord progression viewer into a **comprehensive lead sheet analysis tool** with:
- Roman numeral analysis
- Key center detection & modulation tracking
- Harmonic function color coding (Option C: function colors + key region backgrounds)
- Transition chord annotation
- Editable analysis (like existing chord editing)
- Full lead sheet rendering with melody (Phase 2)
- Export to PDF, MusicXML, MuseScore

---

## Current State (v1.2.2)

HarmonyLab already has:
- ✅ MIDI file parsing
- ✅ Chord progression display
- ✅ Editable chords (dropdown editing)
- ✅ Quiz mode
- ✅ Playback with instrument selection (Grand Piano, Electric Piano, Jazz Guitar)
- ✅ Tempo control

**Missing**:
- ❌ Roman numeral analysis
- ❌ Key center detection
- ❌ Modulation/transition annotation
- ❌ Color coding by function
- ❌ Lead sheet notation rendering
- ❌ Export capabilities

---

## Target User

Jazz pianist (Corey) learning standards. Needs to:
- **Understand** chord progressions, not just memorize
- **See** ii-V-I patterns and common progressions at a glance
- **Identify** modulations and key centers
- **Practice** with color-coded lead sheets
- **Export** for offline study

**Test Repertoire**: 37 jazz standards including:
- Corcovado, Girl from Ipanema, Blue Bossa
- Fly Me to the Moon, Autumn Leaves
- My Funny Valentine, Summertime
- Desafinado, Wave, How Insensitive

---

## Phase 1: Roman Numeral Analysis (P1)

### 1.1 Backend: music21 Integration

**New Dependency**:
```bash
pip install music21 --break-system-packages
```

**New Service** (`app/services/analysis_service.py`):

```python
from music21 import roman, key, harmony, stream
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class HarmonicAnalyzer:
    """Analyze chord progressions using music21."""
    
    FUNCTION_COLORS = {
        'tonic': '#22c55e',        # Green
        'subdominant': '#3b82f6',  # Blue  
        'dominant': '#ef4444',     # Red
        'secondary': '#f59e0b',    # Orange/Yellow
        'chromatic': '#8b5cf6',    # Purple
        'diminished': '#6b7280',   # Gray
        'unknown': '#9ca3af'       # Light gray
    }
    
    def __init__(self):
        self.current_key = None
    
    def analyze_progression(
        self, 
        chords: List[str], 
        key_override: str = None
    ) -> Dict:
        """
        Analyze a full chord progression.
        
        Args:
            chords: List of chord symbols (e.g., ["Dm7", "G7", "Cmaj7"])
            key_override: Manual key (e.g., "C" or "Am")
            
        Returns:
            {
                "detected_key": "C major",
                "confidence": 0.85,
                "chords": [
                    {
                        "index": 0,
                        "symbol": "Dm7",
                        "roman": "ii7",
                        "function": "subdominant",
                        "color": "#3b82f6",
                        "key_context": "C major",
                        "is_secondary": false,
                        "secondary_target": null
                    },
                    ...
                ],
                "key_regions": [...],
                "patterns": [...]
            }
        """
        # Detect or use override key
        if key_override:
            self.current_key = key.Key(key_override)
            confidence = 1.0
        else:
            self.current_key, confidence = self._detect_key(chords)
        
        # Analyze each chord
        analyzed_chords = []
        for i, chord_symbol in enumerate(chords):
            analysis = self._analyze_chord(chord_symbol, i)
            analyzed_chords.append(analysis)
        
        # Detect modulations/key regions
        key_regions = self._detect_key_regions(analyzed_chords)
        
        # Detect common patterns (ii-V-I, etc.)
        patterns = self._detect_patterns(analyzed_chords)
        
        return {
            "detected_key": str(self.current_key),
            "confidence": confidence,
            "chords": analyzed_chords,
            "key_regions": key_regions,
            "patterns": patterns
        }
    
    def _detect_key(self, chords: List[str]) -> tuple:
        """Auto-detect key from chord progression."""
        try:
            s = stream.Stream()
            for symbol in chords:
                try:
                    c = harmony.ChordSymbol(symbol)
                    s.append(c)
                except:
                    continue
            
            detected = s.analyze('key')
            confidence = getattr(detected, 'correlationCoefficient', 0.5)
            return detected, confidence
        except Exception as e:
            logger.warning(f"Key detection failed: {e}")
            return key.Key('C'), 0.0
    
    def _analyze_chord(self, chord_symbol: str, index: int) -> Dict:
        """Analyze a single chord."""
        try:
            c = harmony.ChordSymbol(chord_symbol)
            rn = roman.romanNumeralFromChord(c, self.current_key)
            
            # Determine function
            func = self._get_function(rn)
            
            # Check for secondary dominant
            is_secondary = '/' in rn.figure
            secondary_target = None
            if is_secondary:
                parts = rn.figure.split('/')
                if len(parts) > 1:
                    secondary_target = parts[1]
                func = 'secondary'
            
            return {
                "index": index,
                "symbol": chord_symbol,
                "roman": rn.figure,
                "function": func,
                "color": self.FUNCTION_COLORS.get(func, self.FUNCTION_COLORS['unknown']),
                "key_context": str(self.current_key),
                "is_secondary": is_secondary,
                "secondary_target": secondary_target
            }
        except Exception as e:
            logger.warning(f"Could not analyze {chord_symbol}: {e}")
            return {
                "index": index,
                "symbol": chord_symbol,
                "roman": "?",
                "function": "unknown",
                "color": self.FUNCTION_COLORS['unknown'],
                "key_context": str(self.current_key),
                "is_secondary": False,
                "secondary_target": None
            }
    
    def _get_function(self, rn) -> str:
        """Map Roman numeral to harmonic function."""
        degree = rn.scaleDegree
        
        if degree in [1, 3, 6]:
            return 'tonic'
        elif degree in [2, 4]:
            return 'subdominant'
        elif degree in [5, 7]:
            return 'dominant'
        else:
            return 'chromatic'
    
    def _detect_key_regions(self, chords: List[Dict]) -> List[Dict]:
        """Detect key center changes."""
        regions = []
        current_key = chords[0]['key_context'] if chords else None
        region_start = 0
        
        for i, chord in enumerate(chords):
            if chord['key_context'] != current_key:
                # New key region
                regions.append({
                    "key": current_key,
                    "start_index": region_start,
                    "end_index": i - 1,
                    "transition_type": self._detect_transition_type(chords, i)
                })
                current_key = chord['key_context']
                region_start = i
        
        # Final region
        if chords:
            regions.append({
                "key": current_key,
                "start_index": region_start,
                "end_index": len(chords) - 1,
                "transition_type": None
            })
        
        return regions
    
    def _detect_patterns(self, chords: List[Dict]) -> List[Dict]:
        """Detect ii-V-I and other common patterns."""
        patterns = []
        
        for i in range(len(chords) - 2):
            # Check for ii-V-I
            romans = [chords[i]['roman'], chords[i+1]['roman'], chords[i+2]['roman']]
            
            # Normalize (remove extensions)
            base_romans = [r.split('7')[0].split('9')[0] for r in romans]
            
            if base_romans[0].lower().startswith('ii') and \
               base_romans[1].upper().startswith('V') and \
               base_romans[2].upper().startswith('I'):
                patterns.append({
                    "type": "ii-V-I",
                    "indices": [i, i+1, i+2],
                    "key": chords[i+2]['key_context'],
                    "description": f"ii-V-I in {chords[i+2]['key_context']}"
                })
        
        return patterns
    
    def _detect_transition_type(self, chords: List[Dict], index: int) -> str:
        """Determine how we transitioned to new key."""
        if index == 0:
            return None
        
        prev_chord = chords[index - 1]
        if prev_chord['is_secondary']:
            return "tonicization"
        elif prev_chord['function'] == 'dominant':
            return "modulation"
        else:
            return "direct"
```

---

### 1.2 Database Schema

```sql
-- Store cached analysis (regeneratable)
CREATE TABLE SongAnalysis (
    AnalysisID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL FOREIGN KEY REFERENCES Songs(SongID) ON DELETE CASCADE,
    DetectedKey NVARCHAR(20),
    ManualKeyOverride NVARCHAR(20),
    Confidence FLOAT,
    AnalysisJSON NVARCHAR(MAX),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE(),
    UNIQUE(SongID)
);

-- Store user overrides for individual chords
CREATE TABLE ChordAnalysisOverrides (
    OverrideID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL FOREIGN KEY REFERENCES Songs(SongID) ON DELETE CASCADE,
    ChordIndex INT NOT NULL,
    RomanOverride NVARCHAR(20),
    FunctionOverride NVARCHAR(30),
    KeyContextOverride NVARCHAR(20),
    IsPivotChord BIT DEFAULT 0,
    Notes NVARCHAR(500),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE(),
    UNIQUE(SongID, ChordIndex)
);

-- Store key region annotations
CREATE TABLE KeyRegions (
    RegionID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL FOREIGN KEY REFERENCES Songs(SongID) ON DELETE CASCADE,
    StartChordIndex INT NOT NULL,
    EndChordIndex INT,
    KeyCenter NVARCHAR(20) NOT NULL,
    TransitionType NVARCHAR(30),  -- 'modulation', 'tonicization', 'borrowed', 'direct'
    PivotChordIndex INT,
    Notes NVARCHAR(500),
    IsUserDefined BIT DEFAULT 0,
    CreatedAt DATETIME DEFAULT GETDATE(),
    UNIQUE(SongID, StartChordIndex)
);
```

---

### 1.3 API Endpoints

**New Router** (`app/routers/analysis.py`):

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/songs/{id}/analysis` | Get analysis (cached or generate) |
| POST | `/api/songs/{id}/analysis` | Re-analyze with key override |
| PUT | `/api/songs/{id}/analysis/chord/{index}` | Override single chord analysis |
| DELETE | `/api/songs/{id}/analysis/chord/{index}` | Remove override |
| GET | `/api/songs/{id}/key-regions` | Get key regions |
| POST | `/api/songs/{id}/key-regions` | Add key region |
| PUT | `/api/songs/{id}/key-regions/{id}` | Update key region |
| DELETE | `/api/songs/{id}/key-regions/{id}` | Delete key region |

---

### 1.4 Frontend: Color-Coded Display

**Color Scheme (Option C: Function + Key Region)**:

| Function | Color | Chord Types |
|----------|-------|-------------|
| **Tonic** | 🟢 Green `#22c55e` | I, vi, iii |
| **Subdominant** | 🔵 Blue `#3b82f6` | ii, IV |
| **Dominant** | 🔴 Red `#ef4444` | V, vii° |
| **Secondary** | 🟡 Orange `#f59e0b` | V/x, vii°/x |
| **Chromatic/Borrowed** | 🟣 Purple `#8b5cf6` | bVII, bIII, iv |
| **Diminished** | ⚫ Gray `#6b7280` | °7 passing |

**Key Region Backgrounds**:
- Primary key: White/transparent
- Secondary key: Light blue tint `rgba(219,234,254,0.3)`
- Relative key: Light pink tint `rgba(254,226,226,0.3)`

---

### 1.5 UI Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ Corcovado                                                    🔵 v1.3.0 │
├────────────────────────────────────────────────────────────────────────┤
│ [Start Quiz]  [▶ Play]  Instrument: [Grand Piano ▼]  Tempo: [120] BPM │
├────────────────────────────────────────────────────────────────────────┤
│ Key: [A minor ▼] [Re-analyze]     View: ○ Chords  ● Analysis  ○ Score │
├────────────────────────────────────────────────────────────────────────┤
│ Legend: 🟢 Tonic  🔵 Subdominant  🔴 Dominant  🟡 Secondary  🟣 Borrowed│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ ┌─────────────── A minor ────────────────────────────────────────┐    │
│ │                                                                 │    │
│ │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │    │
│ │  │  Am6   │ │Abdim7  │ │ Gdim7  │ │  C9    │ │ FMaj9  │       │    │
│ │  │   i6   │ │ vii°7  │ │bvii°7  │ │ bIII9  │ │ bVI9   │       │    │
│ │  │  🟢    │ │  🔴    │ │  ⚫    │ │  🟣    │ │  🟣    │       │    │
│ │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │    │
│ │                                   └── borrowed from major ──┘  │    │
│ │                                                                 │    │
│ │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                   │    │
│ │  │  Bb13  │ │  Em7   │ │  Am7   │ │  Am    │                   │    │
│ │  │ bII13  │ │   v7   │ │   i7   │ │   i    │                   │    │
│ │  │  🟣    │ │  🔵    │ │  🟢    │ │  🟢    │   ← click to edit │    │
│ │  └────────┘ └────────┘ └────────┘ └────────┘                   │    │
│ │   tritone                                                       │    │
│ │     sub                                                         │    │
│ └─────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│ ┌─────────────── F major (tonicization) ─────────────────────────┐    │
│ │ Pivot: Em7 functions as v in Am → vii in F                      │    │
│ │                                                                 │    │
│ │  ┌────────┐ ┌────────┐ ┌────────┐ ...                          │    │
│ │  │  Gm7   │ │  C9    │ │  F6/9  │                              │    │
│ │  │  ii7   │ │  V9    │ │  I6/9  │                              │    │
│ │  │  🔵    │ │  🔴    │ │  🟢    │   ← ii-V-I detected          │    │
│ │  └────────┘ └────────┘ └────────┘                              │    │
│ └─────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│ Patterns Detected:                                                     │
│ • ii-V-I in F major (chords 12-14)                                    │
│ • Tritone substitution: Bb13 for E7 (chord 6)                         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 1.6 Chord Edit Modal (Enhanced)

Click any chord to edit its analysis:

```
┌─────────────────────────────────────────────┐
│ Edit Chord Analysis                      ✕  │
├─────────────────────────────────────────────┤
│                                             │
│ Chord Symbol                                │
│ [  Am6                               ▼]    │
│                                             │
│ Roman Numeral                               │
│ [  i6                                ▼]    │
│ Options: i, I, ii, II, iii, III, iv, IV,   │
│          v, V, vi, VI, vii°, bVII, etc.    │
│                                             │
│ Function                                    │
│ [  Tonic                             ▼]    │
│ Options: Tonic, Subdominant, Dominant,     │
│          Secondary, Chromatic, Passing      │
│                                             │
│ Key Context                                 │
│ [  A minor                           ▼]    │
│ (Use to mark start of new key region)       │
│                                             │
│ ☐ Mark as pivot chord                       │
│   Pivots to: [  F major              ▼]    │
│                                             │
│ Notes                                       │
│ [  Tritone sub for E7...            ]      │
│                                             │
│ [Save] [Reset to Auto] [Cancel]             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Phase 2: Lead Sheet Rendering (P2)

### 2.1 VexFlow Integration

```html
<!-- Add to HTML -->
<script src="https://cdn.jsdelivr.net/npm/vexflow@4.2.3/build/cjs/vexflow.js"></script>
```

**Renders**:
- Melody notation from MIDI
- Chord symbols above staff (color-coded)
- Roman numerals below staff
- Key region markers
- Measure numbers

### 2.2 Export Options

| Format | Library | Notes |
|--------|---------|-------|
| PDF | music21 + ReportLab | Requires MuseScore installed on server, OR use client-side SVG→PDF |
| MusicXML | music21 | Standard format, opens in MuseScore/Finale/Sibelius |
| MuseScore | music21 | Generate .mscz directly |

**Export UI**:
```
[📄 Export PDF]  [📝 Export MusicXML]  [🎼 Open in MuseScore]
```

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `app/services/analysis_service.py` | music21 analysis logic |
| `app/routers/analysis.py` | Analysis API endpoints |
| `app/schemas/analysis.py` | Pydantic schemas |
| `frontend/analysis.js` | Analysis UI logic |
| `frontend/analysis.css` | Color-coded styling |
| `frontend/leadsheet-renderer.js` | VexFlow rendering (Phase 2) |

### Modified Files
| File | Changes |
|------|---------|
| `requirements.txt` | Add music21 |
| `app/main.py` | Register analysis router |
| `app/migrations.py` | Add new tables |
| `frontend/song.html` | Add analysis view toggle, legend |
| `frontend/styles.css` | Function colors |

---

## Implementation Order

### Phase 1A: Backend (4-5 hrs)
1. Install music21
2. Create analysis_service.py
3. Create database tables
4. Create analysis router + endpoints
5. Test with Corcovado

### Phase 1B: Frontend (4-5 hrs)
1. Add Analysis view toggle
2. Create color-coded chord grid
3. Add Roman numeral display
4. Add function legend
5. Add key region grouping

### Phase 1C: Editing (2-3 hrs)
1. Enhance chord edit modal
2. Add override API calls
3. Merge overrides with analysis
4. Key region editing

### Phase 2A: Lead Sheet (6-8 hrs)
1. Integrate VexFlow
2. Render melody from MIDI
3. Add colored chord symbols
4. Add Roman numerals
5. Key signatures, time signatures

### Phase 2B: Export (3-4 hrs)
1. MusicXML export
2. PDF export
3. MuseScore format
4. Download buttons

---

## Acceptance Criteria

### Phase 1 (v1.3.0)
- [ ] Auto-detect key from chord progression
- [ ] Display Roman numerals for all chords
- [ ] Color-code chords by harmonic function
- [ ] Show function legend
- [ ] Group chords by key region (background tint)
- [ ] Mark modulations/tonicizations
- [ ] Detect ii-V-I patterns
- [ ] Click chord to edit analysis
- [ ] Override Roman numeral via dropdown
- [ ] Override function via dropdown
- [ ] Mark key region changes
- [ ] Mark pivot chords
- [ ] Overrides persist in database
- [ ] Reset override to auto-detect

### Phase 2 (v1.4.0)
- [ ] Render melody notation (VexFlow)
- [ ] Show chord symbols above staff
- [ ] Show Roman numerals below staff
- [ ] Color-code chord symbols
- [ ] Mark key regions
- [ ] Export to PDF
- [ ] Export to MusicXML
- [ ] MusicXML opens correctly in MuseScore

---

## Test Songs

| Song | Key | Test Focus |
|------|-----|------------|
| Corcovado | Am | Modal interchange, borrowed chords |
| Girl from Ipanema | F | Key center change (F → Gb → F) |
| Blue Bossa | Cm | Clear modulation (Cm → Db → Cm) |
| Autumn Leaves | Gm | ii-V-I patterns, relative major |
| Fly Me to the Moon | C | Standard ii-V-I progressions |
| Desafinado | F | Chromaticism, secondary dominants |

---

## Version

After Phase 1: **v1.3.0**
After Phase 2: **v1.4.0**
