# [HarmonyLab] 🔵 Lead Sheet Analysis Feature (v1.3.0)

**Read first**: `CLAUDE.md` and `HarmonyLab_LeadSheet_Analysis_Design.md`

---

## Overview

Add Roman numeral analysis, harmonic function color-coding, and key center detection to HarmonyLab. This transforms it from a chord progression viewer into a learning tool that helps understand *why* chord progressions work.

**Version**: 1.2.2 → 1.3.0

---

## Phase 1 Only (This Sprint)

Focus on analysis and display. Lead sheet rendering (VexFlow) is Phase 2.

---

## Dependencies

```bash
pip install music21 --break-system-packages
```

---

## Database Migrations

Add to `app/migrations.py`:

```sql
-- Cached analysis results
CREATE TABLE IF NOT EXISTS SongAnalysis (
    AnalysisID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL,
    DetectedKey NVARCHAR(20),
    ManualKeyOverride NVARCHAR(20),
    Confidence FLOAT,
    AnalysisJSON NVARCHAR(MAX),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (SongID) REFERENCES Songs(SongID) ON DELETE CASCADE,
    CONSTRAINT UQ_SongAnalysis_SongID UNIQUE (SongID)
);

-- User overrides for individual chords
CREATE TABLE IF NOT EXISTS ChordAnalysisOverrides (
    OverrideID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL,
    ChordIndex INT NOT NULL,
    RomanOverride NVARCHAR(20),
    FunctionOverride NVARCHAR(30),
    KeyContextOverride NVARCHAR(20),
    IsPivotChord BIT DEFAULT 0,
    PivotToKey NVARCHAR(20),
    Notes NVARCHAR(500),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (SongID) REFERENCES Songs(SongID) ON DELETE CASCADE,
    CONSTRAINT UQ_ChordOverride UNIQUE (SongID, ChordIndex)
);

-- Key region annotations
CREATE TABLE IF NOT EXISTS KeyRegions (
    RegionID INT IDENTITY(1,1) PRIMARY KEY,
    SongID INT NOT NULL,
    StartChordIndex INT NOT NULL,
    EndChordIndex INT,
    KeyCenter NVARCHAR(20) NOT NULL,
    TransitionType NVARCHAR(30),
    PivotChordIndex INT,
    Notes NVARCHAR(500),
    IsUserDefined BIT DEFAULT 0,
    CreatedAt DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (SongID) REFERENCES Songs(SongID) ON DELETE CASCADE,
    CONSTRAINT UQ_KeyRegion UNIQUE (SongID, StartChordIndex)
);
```

---

## Backend: Analysis Service

**Create** `app/services/analysis_service.py`:

```python
from music21 import roman, key, harmony, stream
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class HarmonicAnalyzer:
    """Analyze chord progressions using music21."""
    
    FUNCTION_COLORS = {
        'tonic': '#22c55e',        # Green
        'subdominant': '#3b82f6',  # Blue  
        'dominant': '#ef4444',     # Red
        'secondary': '#f59e0b',    # Orange
        'chromatic': '#8b5cf6',    # Purple
        'diminished': '#6b7280',   # Gray
        'unknown': '#9ca3af'
    }
    
    def __init__(self):
        self.current_key = None
    
    def analyze_progression(self, chords: List[str], key_override: str = None) -> Dict:
        """Analyze full chord progression."""
        
        # Detect or use override key
        if key_override:
            self.current_key = key.Key(key_override)
            confidence = 1.0
        else:
            self.current_key, confidence = self._detect_key(chords)
        
        # Analyze each chord
        analyzed = []
        for i, symbol in enumerate(chords):
            analysis = self._analyze_chord(symbol, i)
            analyzed.append(analysis)
        
        # Detect patterns
        patterns = self._detect_patterns(analyzed)
        
        return {
            "detected_key": str(self.current_key),
            "confidence": confidence,
            "chords": analyzed,
            "patterns": patterns
        }
    
    def _detect_key(self, chords: List[str]) -> tuple:
        """Auto-detect key from chords."""
        try:
            s = stream.Stream()
            for symbol in chords[:16]:  # Use first 16 chords
                try:
                    c = harmony.ChordSymbol(symbol)
                    s.append(c)
                except:
                    continue
            
            detected = s.analyze('key')
            conf = getattr(detected, 'correlationCoefficient', 0.5)
            return detected, conf
        except Exception as e:
            logger.warning(f"Key detection failed: {e}")
            return key.Key('C'), 0.0
    
    def _analyze_chord(self, symbol: str, index: int) -> Dict:
        """Analyze single chord."""
        try:
            c = harmony.ChordSymbol(symbol)
            rn = roman.romanNumeralFromChord(c, self.current_key)
            
            func = self._get_function(rn)
            is_secondary = '/' in rn.figure
            secondary_target = None
            
            if is_secondary:
                parts = rn.figure.split('/')
                if len(parts) > 1:
                    secondary_target = parts[1]
                func = 'secondary'
            
            return {
                "index": index,
                "symbol": symbol,
                "roman": rn.figure,
                "function": func,
                "color": self.FUNCTION_COLORS.get(func, self.FUNCTION_COLORS['unknown']),
                "key_context": str(self.current_key),
                "is_secondary": is_secondary,
                "secondary_target": secondary_target
            }
        except Exception as e:
            logger.warning(f"Could not analyze {symbol}: {e}")
            return {
                "index": index,
                "symbol": symbol,
                "roman": "?",
                "function": "unknown",
                "color": self.FUNCTION_COLORS['unknown'],
                "key_context": str(self.current_key),
                "is_secondary": False,
                "secondary_target": None
            }
    
    def _get_function(self, rn) -> str:
        """Map scale degree to function."""
        degree = rn.scaleDegree
        if degree in [1, 3, 6]:
            return 'tonic'
        elif degree in [2, 4]:
            return 'subdominant'
        elif degree in [5, 7]:
            return 'dominant'
        return 'chromatic'
    
    def _detect_patterns(self, chords: List[Dict]) -> List[Dict]:
        """Detect ii-V-I and other patterns."""
        patterns = []
        
        for i in range(len(chords) - 2):
            r1 = chords[i]['roman'].lower()
            r2 = chords[i+1]['roman'].lower()
            r3 = chords[i+2]['roman'].lower()
            
            # ii-V-I detection (simplified)
            if r1.startswith('ii') and r2.startswith('v') and r3.startswith('i'):
                patterns.append({
                    "type": "ii-V-I",
                    "indices": [i, i+1, i+2],
                    "description": f"ii-V-I in {chords[i+2]['key_context']}"
                })
        
        return patterns


def analyze_song(chords: List[str], key_override: str = None) -> Dict:
    """Main entry point."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_progression(chords, key_override)
```

---

## Backend: API Router

**Create** `app/routers/analysis.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from ..services.analysis_service import analyze_song
from ..database import get_db
import json

router = APIRouter(prefix="/api/songs", tags=["analysis"])


class AnalysisRequest(BaseModel):
    key_override: Optional[str] = None


class ChordOverrideRequest(BaseModel):
    roman: Optional[str] = None
    function: Optional[str] = None
    key_context: Optional[str] = None
    is_pivot: bool = False
    pivot_to_key: Optional[str] = None
    notes: Optional[str] = None


@router.get("/{song_id}/analysis")
async def get_analysis(song_id: int, refresh: bool = False, db = Depends(get_db)):
    """Get harmonic analysis for a song."""
    
    # Check cache unless refresh requested
    if not refresh:
        cached = db.execute(
            "SELECT AnalysisJSON, ManualKeyOverride FROM SongAnalysis WHERE SongID = ?",
            (song_id,)
        ).fetchone()
        
        if cached and cached['AnalysisJSON']:
            result = json.loads(cached['AnalysisJSON'])
            return apply_overrides(result, song_id, db)
    
    # Get chords from song
    song = db.execute("SELECT * FROM Songs WHERE SongID = ?", (song_id,)).fetchone()
    if not song:
        raise HTTPException(404, "Song not found")
    
    chords = db.execute(
        "SELECT Symbol FROM SongChords WHERE SongID = ? ORDER BY Position",
        (song_id,)
    ).fetchall()
    
    chord_symbols = [c['Symbol'] for c in chords]
    
    # Get key override if set
    key_override = None
    cached = db.execute(
        "SELECT ManualKeyOverride FROM SongAnalysis WHERE SongID = ?",
        (song_id,)
    ).fetchone()
    if cached:
        key_override = cached['ManualKeyOverride']
    
    # Run analysis
    result = analyze_song(chord_symbols, key_override)
    
    # Cache result
    db.execute("""
        MERGE INTO SongAnalysis AS target
        USING (SELECT ? AS SongID) AS source
        ON target.SongID = source.SongID
        WHEN MATCHED THEN UPDATE SET 
            AnalysisJSON = ?, DetectedKey = ?, Confidence = ?, UpdatedAt = GETDATE()
        WHEN NOT MATCHED THEN INSERT 
            (SongID, AnalysisJSON, DetectedKey, Confidence)
            VALUES (?, ?, ?, ?);
    """, (song_id, json.dumps(result), result['detected_key'], result['confidence'],
          song_id, json.dumps(result), result['detected_key'], result['confidence']))
    db.commit()
    
    return apply_overrides(result, song_id, db)


@router.post("/{song_id}/analysis")
async def update_analysis_key(song_id: int, request: AnalysisRequest, db = Depends(get_db)):
    """Re-analyze with manual key override."""
    
    # Save key override
    db.execute("""
        MERGE INTO SongAnalysis AS target
        USING (SELECT ? AS SongID) AS source
        ON target.SongID = source.SongID
        WHEN MATCHED THEN UPDATE SET ManualKeyOverride = ?, UpdatedAt = GETDATE()
        WHEN NOT MATCHED THEN INSERT (SongID, ManualKeyOverride) VALUES (?, ?);
    """, (song_id, request.key_override, song_id, request.key_override))
    db.commit()
    
    # Refresh analysis
    return await get_analysis(song_id, refresh=True, db=db)


@router.put("/{song_id}/analysis/chord/{chord_index}")
async def override_chord(
    song_id: int, 
    chord_index: int, 
    override: ChordOverrideRequest,
    db = Depends(get_db)
):
    """Override analysis for a specific chord."""
    
    db.execute("""
        MERGE INTO ChordAnalysisOverrides AS target
        USING (SELECT ? AS SongID, ? AS ChordIndex) AS source
        ON target.SongID = source.SongID AND target.ChordIndex = source.ChordIndex
        WHEN MATCHED THEN UPDATE SET 
            RomanOverride = ?, FunctionOverride = ?, KeyContextOverride = ?,
            IsPivotChord = ?, PivotToKey = ?, Notes = ?, UpdatedAt = GETDATE()
        WHEN NOT MATCHED THEN INSERT 
            (SongID, ChordIndex, RomanOverride, FunctionOverride, KeyContextOverride, 
             IsPivotChord, PivotToKey, Notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        song_id, chord_index,
        override.roman, override.function, override.key_context,
        override.is_pivot, override.pivot_to_key, override.notes,
        song_id, chord_index, override.roman, override.function, override.key_context,
        override.is_pivot, override.pivot_to_key, override.notes
    ))
    db.commit()
    
    return {"status": "updated", "chord_index": chord_index}


@router.delete("/{song_id}/analysis/chord/{chord_index}")
async def delete_chord_override(song_id: int, chord_index: int, db = Depends(get_db)):
    """Remove override, revert to auto-analysis."""
    
    db.execute(
        "DELETE FROM ChordAnalysisOverrides WHERE SongID = ? AND ChordIndex = ?",
        (song_id, chord_index)
    )
    db.commit()
    
    return {"status": "deleted", "chord_index": chord_index}


def apply_overrides(result: dict, song_id: int, db) -> dict:
    """Apply user overrides to analysis result."""
    
    overrides = db.execute(
        "SELECT * FROM ChordAnalysisOverrides WHERE SongID = ?",
        (song_id,)
    ).fetchall()
    
    override_map = {o['ChordIndex']: o for o in overrides}
    
    for chord in result['chords']:
        idx = chord['index']
        if idx in override_map:
            o = override_map[idx]
            if o['RomanOverride']:
                chord['roman'] = o['RomanOverride']
                chord['is_override'] = True
            if o['FunctionOverride']:
                chord['function'] = o['FunctionOverride']
                # Update color based on function
                chord['color'] = get_function_color(o['FunctionOverride'])
            if o['KeyContextOverride']:
                chord['key_context'] = o['KeyContextOverride']
            if o['IsPivotChord']:
                chord['is_pivot'] = True
                chord['pivot_to_key'] = o['PivotToKey']
            if o['Notes']:
                chord['notes'] = o['Notes']
    
    return result


def get_function_color(func: str) -> str:
    colors = {
        'tonic': '#22c55e',
        'subdominant': '#3b82f6',
        'dominant': '#ef4444',
        'secondary': '#f59e0b',
        'chromatic': '#8b5cf6',
        'diminished': '#6b7280',
        'unknown': '#9ca3af'
    }
    return colors.get(func, colors['unknown'])
```

**Register router** in `app/main.py`:
```python
from .routers import analysis
app.include_router(analysis.router)
```

---

## Frontend: CSS Colors

**Add to** `frontend/styles.css` (or create `analysis.css`):

```css
/* Function colors */
.chord-function-tonic { 
    background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.05));
    border-left: 4px solid #22c55e;
}

.chord-function-subdominant { 
    background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(59,130,246,0.05));
    border-left: 4px solid #3b82f6;
}

.chord-function-dominant { 
    background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(239,68,68,0.05));
    border-left: 4px solid #ef4444;
}

.chord-function-secondary { 
    background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.05));
    border-left: 4px solid #f59e0b;
}

.chord-function-chromatic { 
    background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.05));
    border-left: 4px solid #8b5cf6;
}

.chord-function-diminished { 
    background: linear-gradient(135deg, rgba(107,114,128,0.2), rgba(107,114,128,0.05));
    border-left: 4px solid #6b7280;
}

/* Chord card */
.chord-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 14px;
    border-radius: 8px;
    min-width: 70px;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
}

.chord-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.chord-card .chord-symbol {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1f2937;
}

.chord-card .roman-numeral {
    font-size: 0.9rem;
    font-weight: 500;
    color: #4b5563;
    font-style: italic;
    margin-top: 2px;
}

.chord-card .secondary-target {
    font-size: 0.7rem;
    color: #f59e0b;
    margin-top: 2px;
}

.chord-card.is-override {
    border-style: dashed;
}

/* Legend */
.function-legend {
    display: flex;
    gap: 16px;
    padding: 8px 16px;
    background: #f3f4f6;
    border-radius: 6px;
    font-size: 0.85rem;
    flex-wrap: wrap;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 3px;
}

.legend-dot.tonic { background: #22c55e; }
.legend-dot.subdominant { background: #3b82f6; }
.legend-dot.dominant { background: #ef4444; }
.legend-dot.secondary { background: #f59e0b; }
.legend-dot.chromatic { background: #8b5cf6; }

/* Key region */
.key-region {
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 8px;
    background: rgba(255,255,255,0.5);
}

.key-region-header {
    font-size: 0.85rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #e5e7eb;
}

.key-region-secondary {
    background: rgba(219,234,254,0.3);
}

/* Patterns */
.pattern-highlight {
    position: relative;
}

.pattern-highlight::after {
    content: 'ii-V-I';
    position: absolute;
    bottom: -18px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.7rem;
    color: #6b7280;
    white-space: nowrap;
}
```

---

## Frontend: JavaScript

**Update** song page to add analysis toggle and rendering.

Key functions needed:
1. `loadAnalysis(songId)` — Fetch from API
2. `renderAnalysis(data)` — Display color-coded chords
3. `openChordEditor(chordIndex)` — Modal for overrides
4. `saveChordOverride(songId, index, data)` — Save override
5. `reanalyze(songId, key)` — Refresh with new key

---

## UI Changes

### Add to song page header:
```html
<div class="analysis-controls">
    <label>Key:</label>
    <select id="key-select">
        <option value="">Auto-detect</option>
        <option value="C">C major</option>
        <option value="Am">A minor</option>
        <option value="G">G major</option>
        <option value="Em">E minor</option>
        <option value="D">D major</option>
        <option value="Bm">B minor</option>
        <option value="F">F major</option>
        <option value="Dm">D minor</option>
        <option value="Bb">Bb major</option>
        <option value="Gm">G minor</option>
        <option value="Eb">Eb major</option>
        <option value="Cm">C minor</option>
        <!-- Add more as needed -->
    </select>
    <button id="reanalyze-btn">Re-analyze</button>
</div>

<div class="view-toggle">
    <label><input type="radio" name="view" value="chords" checked> Chords</label>
    <label><input type="radio" name="view" value="analysis"> Analysis</label>
</div>
```

### Add legend:
```html
<div class="function-legend">
    <span class="legend-item"><span class="legend-dot tonic"></span> Tonic</span>
    <span class="legend-item"><span class="legend-dot subdominant"></span> Subdominant</span>
    <span class="legend-item"><span class="legend-dot dominant"></span> Dominant</span>
    <span class="legend-item"><span class="legend-dot secondary"></span> Secondary</span>
    <span class="legend-item"><span class="legend-dot chromatic"></span> Chromatic</span>
</div>
```

---

## Testing

### Test with Corcovado
1. Load song
2. Toggle to Analysis view
3. Verify Roman numerals appear
4. Verify colors match functions
5. Click chord → edit modal opens
6. Override a Roman numeral
7. Verify override persists on reload
8. Change key → re-analyze → verify new Roman numerals

### Verify:
- [ ] music21 installed and working
- [ ] Database tables created
- [ ] API returns analysis
- [ ] Colors display correctly
- [ ] Overrides save and load
- [ ] Key dropdown works
- [ ] Re-analyze works

---

## Version Bump

Update to **v1.3.0** in:
- `app/config.py`
- `app/main.py`
- `frontend/index.html`
- Any footer references

---

## Deployment

1. Install music21: `pip install music21 --break-system-packages`
2. Run database migrations
3. Deploy backend
4. Deploy frontend
5. Test with Corcovado

---

## Do NOT Implement (Phase 2)

- VexFlow notation rendering
- Lead sheet view
- PDF export
- MusicXML export
- MuseScore export

These are Phase 2 (v1.4.0).

---

## Acceptance Criteria

- [ ] API returns Roman numerals for Corcovado
- [ ] Key auto-detected (should be Am)
- [ ] Chords color-coded by function
- [ ] Legend visible
- [ ] Click chord opens edit modal
- [ ] Can override Roman numeral
- [ ] Can override function
- [ ] Overrides persist
- [ ] Can reset to auto
- [ ] Key dropdown allows manual selection
- [ ] Re-analyze updates display
- [ ] Version shows 1.3.0
