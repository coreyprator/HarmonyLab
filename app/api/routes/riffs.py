"""
Jazz Riff Library API Routes (HL-048)
Serves a curated library of common jazz riffs with MIDI note data for playback.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/riffs", tags=["riffs"])


class RiffNote(BaseModel):
    midi: int
    duration: float  # beats
    beat: float  # beat position within pattern


class Riff(BaseModel):
    id: str
    name: str
    key: str
    context: str
    description: str
    tempo: int
    time_signature: str
    notes: List[RiffNote]
    tags: List[str]


# Seed data: 10 common jazz riffs
# MIDI note reference: C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71
RIFF_LIBRARY: List[dict] = [
    {
        "id": "ii-v-i-basic",
        "name": "Basic ii-V-I line",
        "key": "C major",
        "context": "Dm7 → G7 → Cmaj7",
        "description": "The most common jazz progression. Ascending stepwise line through ii-V resolving to I.",
        "tempo": 120,
        "time_signature": "4/4",
        "notes": [
            # Dm7: D E F A
            {"midi": 62, "duration": 1.0, "beat": 1.0},
            {"midi": 64, "duration": 1.0, "beat": 2.0},
            {"midi": 65, "duration": 1.0, "beat": 3.0},
            {"midi": 69, "duration": 1.0, "beat": 4.0},
            # G7: G A B D
            {"midi": 67, "duration": 1.0, "beat": 5.0},
            {"midi": 69, "duration": 1.0, "beat": 6.0},
            {"midi": 71, "duration": 1.0, "beat": 7.0},
            {"midi": 74, "duration": 1.0, "beat": 8.0},
            # Cmaj7: C E G B
            {"midi": 72, "duration": 2.0, "beat": 9.0},
            {"midi": 76, "duration": 2.0, "beat": 11.0},
        ],
        "tags": ["ii-V-I", "beginner", "stepwise"],
    },
    {
        "id": "bebop-scale-run",
        "name": "Bebop scale run",
        "key": "C major",
        "context": "Cmaj7",
        "description": "Descending C bebop major scale (adds passing tone between 8 and 7). Classic Charlie Parker vocabulary.",
        "tempo": 160,
        "time_signature": "4/4",
        "notes": [
            {"midi": 84, "duration": 0.5, "beat": 1.0},   # C5
            {"midi": 83, "duration": 0.5, "beat": 1.5},   # B4 (passing)
            {"midi": 81, "duration": 0.5, "beat": 2.0},   # A4 (natural 7→6 bebop passing)
            {"midi": 79, "duration": 0.5, "beat": 2.5},   # G4
            {"midi": 77, "duration": 0.5, "beat": 3.0},   # F4
            {"midi": 76, "duration": 0.5, "beat": 3.5},   # E4
            {"midi": 74, "duration": 0.5, "beat": 4.0},   # D4
            {"midi": 72, "duration": 1.0, "beat": 4.5},   # C4 resolve
        ],
        "tags": ["bebop", "scale", "descending"],
    },
    {
        "id": "parker-turnaround",
        "name": "Charlie Parker turnaround",
        "key": "Bb major",
        "context": "I → VI → ii → V",
        "description": "Bird's signature turnaround lick over Bb rhythm changes. Chromatic approach to each chord tone.",
        "tempo": 180,
        "time_signature": "4/4",
        "notes": [
            # Bbmaj7: Bb D F
            {"midi": 70, "duration": 0.5, "beat": 1.0},   # Bb4
            {"midi": 74, "duration": 0.5, "beat": 1.5},   # D5
            {"midi": 77, "duration": 1.0, "beat": 2.0},   # F5
            # G7: chromatic approach
            {"midi": 76, "duration": 0.5, "beat": 3.0},   # E5
            {"midi": 75, "duration": 0.5, "beat": 3.5},   # Eb5 (chromatic)
            {"midi": 74, "duration": 1.0, "beat": 4.0},   # D5
            # Cm7: C Eb G
            {"midi": 72, "duration": 0.5, "beat": 5.0},   # C5
            {"midi": 75, "duration": 0.5, "beat": 5.5},   # Eb5
            {"midi": 67, "duration": 1.0, "beat": 6.0},   # G4
            # F7: resolve
            {"midi": 65, "duration": 1.0, "beat": 7.0},   # F4
            {"midi": 69, "duration": 1.0, "beat": 8.0},   # A4
        ],
        "tags": ["turnaround", "Parker", "chromatic"],
    },
    {
        "id": "tritone-sub",
        "name": "Tritone substitution lick",
        "key": "C major",
        "context": "V7 → bII7",
        "description": "Tritone substitution: Db7 replaces G7. Half-step resolution Db→C gives smooth voice leading.",
        "tempo": 120,
        "time_signature": "4/4",
        "notes": [
            # G7 setup
            {"midi": 67, "duration": 0.5, "beat": 1.0},   # G4
            {"midi": 71, "duration": 0.5, "beat": 1.5},   # B4
            {"midi": 74, "duration": 1.0, "beat": 2.0},   # D5
            # Db7 tritone sub
            {"midi": 73, "duration": 0.5, "beat": 3.0},   # Db5
            {"midi": 72, "duration": 0.5, "beat": 3.5},   # C5 (chromatic approach)
            {"midi": 70, "duration": 0.5, "beat": 4.0},   # Bb4
            {"midi": 68, "duration": 0.5, "beat": 4.5},   # Ab4
            # Cmaj7 resolution
            {"midi": 67, "duration": 1.0, "beat": 5.0},   # G4
            {"midi": 72, "duration": 1.0, "beat": 6.0},   # C5
        ],
        "tags": ["tritone", "substitution", "voice-leading"],
    },
    {
        "id": "coltrane-changes",
        "name": "Coltrane changes phrase",
        "key": "C major",
        "context": "Giant Steps pattern",
        "description": "Major third cycle: Cmaj7→Eb7→Abmaj7→B7→Emaj7→G7→C. Coltrane's signature harmonic movement.",
        "tempo": 200,
        "time_signature": "4/4",
        "notes": [
            # Cmaj7: C E
            {"midi": 72, "duration": 0.5, "beat": 1.0},
            {"midi": 76, "duration": 0.5, "beat": 1.5},
            # Eb7: Eb G
            {"midi": 75, "duration": 0.5, "beat": 2.0},
            {"midi": 79, "duration": 0.5, "beat": 2.5},
            # Abmaj7: Ab C
            {"midi": 80, "duration": 0.5, "beat": 3.0},
            {"midi": 84, "duration": 0.5, "beat": 3.5},
            # B7: B D#
            {"midi": 71, "duration": 0.5, "beat": 4.0},
            {"midi": 75, "duration": 0.5, "beat": 4.5},
            # Emaj7: E G#
            {"midi": 76, "duration": 0.5, "beat": 5.0},
            {"midi": 80, "duration": 0.5, "beat": 5.5},
            # G7 → C resolution
            {"midi": 79, "duration": 0.5, "beat": 6.0},
            {"midi": 74, "duration": 0.5, "beat": 6.5},
            {"midi": 72, "duration": 1.0, "beat": 7.0},
        ],
        "tags": ["Coltrane", "Giant Steps", "major thirds"],
    },
    {
        "id": "blues-scale-run",
        "name": "Blues scale run",
        "key": "Bb major",
        "context": "I7",
        "description": "Bb blues scale ascending and descending over a Bb7 chord. Essential blues-jazz vocabulary.",
        "tempo": 120,
        "time_signature": "4/4",
        "notes": [
            {"midi": 58, "duration": 0.5, "beat": 1.0},   # Bb3
            {"midi": 61, "duration": 0.5, "beat": 1.5},   # Db4
            {"midi": 63, "duration": 0.5, "beat": 2.0},   # Eb4
            {"midi": 64, "duration": 0.5, "beat": 2.5},   # E4 (blue note)
            {"midi": 65, "duration": 0.5, "beat": 3.0},   # F4
            {"midi": 68, "duration": 0.5, "beat": 3.5},   # Ab4
            {"midi": 70, "duration": 0.5, "beat": 4.0},   # Bb4
            # Descend
            {"midi": 68, "duration": 0.5, "beat": 4.5},   # Ab4
            {"midi": 65, "duration": 0.5, "beat": 5.0},   # F4
            {"midi": 64, "duration": 0.5, "beat": 5.5},   # E4
            {"midi": 63, "duration": 0.5, "beat": 6.0},   # Eb4
            {"midi": 61, "duration": 0.5, "beat": 6.5},   # Db4
            {"midi": 58, "duration": 1.0, "beat": 7.0},   # Bb3
        ],
        "tags": ["blues", "scale", "essential"],
    },
    {
        "id": "rhythm-changes-head",
        "name": "Rhythm changes head",
        "key": "Bb major",
        "context": "I → VI → ii → V",
        "description": "Classic A-section melody outline from 'I Got Rhythm' changes. Foundation of countless jazz standards.",
        "tempo": 160,
        "time_signature": "4/4",
        "notes": [
            # Bbmaj7
            {"midi": 70, "duration": 1.0, "beat": 1.0},   # Bb4
            {"midi": 74, "duration": 0.5, "beat": 2.0},   # D5
            {"midi": 70, "duration": 0.5, "beat": 2.5},   # Bb4
            # G7
            {"midi": 71, "duration": 1.0, "beat": 3.0},   # B4
            {"midi": 67, "duration": 1.0, "beat": 4.0},   # G4
            # Cm7
            {"midi": 72, "duration": 1.0, "beat": 5.0},   # C5
            {"midi": 75, "duration": 0.5, "beat": 6.0},   # Eb5
            {"midi": 72, "duration": 0.5, "beat": 6.5},   # C5
            # F7
            {"midi": 69, "duration": 1.0, "beat": 7.0},   # A4
            {"midi": 65, "duration": 1.0, "beat": 8.0},   # F4
        ],
        "tags": ["rhythm changes", "standard", "bebop"],
    },
    {
        "id": "autumn-leaves-ii-v",
        "name": "Autumn Leaves ii-V",
        "key": "G minor",
        "context": "Am7b5 → D7 → Gm",
        "description": "The classic minor ii-V-i from Autumn Leaves. Half-diminished to dominant 7 resolving to minor.",
        "tempo": 120,
        "time_signature": "4/4",
        "notes": [
            # Am7b5: A C Eb G
            {"midi": 69, "duration": 1.0, "beat": 1.0},   # A4
            {"midi": 72, "duration": 1.0, "beat": 2.0},   # C5
            {"midi": 75, "duration": 1.0, "beat": 3.0},   # Eb5
            {"midi": 67, "duration": 1.0, "beat": 4.0},   # G4
            # D7: D F# A C
            {"midi": 74, "duration": 1.0, "beat": 5.0},   # D5
            {"midi": 66, "duration": 1.0, "beat": 6.0},   # F#4
            {"midi": 69, "duration": 1.0, "beat": 7.0},   # A4
            # Gm resolution
            {"midi": 67, "duration": 2.0, "beat": 8.0},   # G4
        ],
        "tags": ["minor ii-V-i", "Autumn Leaves", "standard"],
    },
    {
        "id": "modal-vamp",
        "name": "Modal vamp",
        "key": "D dorian",
        "context": "Dm7 → Em7",
        "description": "Miles Davis-style modal vamp. Two-chord comping pattern with dorian color tones.",
        "tempo": 100,
        "time_signature": "4/4",
        "notes": [
            # Dm7 voicing
            {"midi": 62, "duration": 1.5, "beat": 1.0},   # D4
            {"midi": 65, "duration": 1.5, "beat": 1.0},   # F4
            {"midi": 69, "duration": 1.5, "beat": 1.0},   # A4
            {"midi": 72, "duration": 1.5, "beat": 1.0},   # C5
            # Em7 voicing
            {"midi": 64, "duration": 1.5, "beat": 3.0},   # E4
            {"midi": 67, "duration": 1.5, "beat": 3.0},   # G4
            {"midi": 71, "duration": 1.5, "beat": 3.0},   # B4
            {"midi": 74, "duration": 1.5, "beat": 3.0},   # D5
            # Back to Dm7
            {"midi": 62, "duration": 2.0, "beat": 5.0},   # D4
            {"midi": 65, "duration": 2.0, "beat": 5.0},   # F4
            {"midi": 69, "duration": 2.0, "beat": 5.0},   # A4
            {"midi": 72, "duration": 2.0, "beat": 5.0},   # C5
        ],
        "tags": ["modal", "Miles Davis", "vamp"],
    },
    {
        "id": "chromatic-approach",
        "name": "Chromatic approach",
        "key": "C major",
        "context": "Target chord approach",
        "description": "Chromatic enclosure: approach each chord tone from a half step above and below. Universal jazz technique.",
        "tempo": 140,
        "time_signature": "4/4",
        "notes": [
            # Approach C from above and below
            {"midi": 73, "duration": 0.5, "beat": 1.0},   # Db (above)
            {"midi": 71, "duration": 0.5, "beat": 1.5},   # B (below)
            {"midi": 72, "duration": 1.0, "beat": 2.0},   # C target
            # Approach E
            {"midi": 66, "duration": 0.5, "beat": 3.0},   # F# (above)
            {"midi": 63, "duration": 0.5, "beat": 3.5},   # Eb (below)
            {"midi": 64, "duration": 1.0, "beat": 4.0},   # E target
            # Approach G
            {"midi": 68, "duration": 0.5, "beat": 5.0},   # Ab (above)
            {"midi": 66, "duration": 0.5, "beat": 5.5},   # F# (below)
            {"midi": 67, "duration": 1.0, "beat": 6.0},   # G target
            # Resolve to C
            {"midi": 72, "duration": 2.0, "beat": 7.0},   # C5
        ],
        "tags": ["chromatic", "enclosure", "technique"],
    },
]


@router.get("/")
async def list_riffs(
    key: Optional[str] = Query(None, description="Filter by key (e.g. 'C major', 'Bb')"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
):
    """List all jazz riffs, optionally filtered by key or tag."""
    results = RIFF_LIBRARY
    if key:
        key_lower = key.lower()
        results = [r for r in results if key_lower in r["key"].lower()]
    if tag:
        tag_lower = tag.lower()
        results = [r for r in results if any(tag_lower in t.lower() for t in r["tags"])]
    return {"riffs": results, "total": len(results)}


@router.get("/{riff_id}")
async def get_riff(riff_id: str):
    """Get a single riff by ID."""
    for r in RIFF_LIBRARY:
        if r["id"] == riff_id:
            return r
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Riff '{riff_id}' not found")
