"""
HarmonyLab Harmonic Analysis Service
Uses music21 for Roman numeral analysis, key detection, and pattern recognition.
"""
from music21 import roman, key, harmony, stream, chord
from typing import List, Dict, Optional
import logging

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
                    normalized = self._normalize_chord_symbol(symbol)
                    cs = harmony.ChordSymbol(normalized)
                    # Convert to plain Chord — ChordSymbol objects confuse
                    # the Krumhansl-Schmuckler algorithm in music21.
                    c = chord.Chord(cs.pitches)
                    s.append(c)
                except Exception:
                    continue

            detected = s.analyze('key')
            conf = getattr(detected, 'correlationCoefficient', 0.5)
            return detected, conf
        except Exception as e:
            logger.warning(f"Key detection failed: {e}")
            return key.Key('C'), 0.0

    def _normalize_chord_symbol(self, symbol: str) -> str:
        """Normalize chord symbols for music21 parsing.

        Key conversions:
        - 'b' flats in root → '-' (music21 format): Ab → A-, Bb7 → B-7
        - 'Maj' suffix without number → remove: BbMaj → B-
        """
        import re

        # Convert flat 'b' in root to '-' (music21 format)
        # Pattern: letter + 'b' at position 2 → letter + '-'
        # "Ab" → "A-", "Bb7" → "B-7", "Abm7" → "A-m7"
        match = re.match(r'^([A-G])b(.*)$', symbol)
        if match:
            symbol = match.group(1) + '-' + match.group(2)

        # Handle "Maj" suffix (without number) - remove it
        # "CMaj" → "C", "A-Maj" → "A-"
        if symbol.endswith('Maj') and not any(c.isdigit() for c in symbol):
            symbol = symbol[:-3]

        return symbol

    def _analyze_chord(self, symbol: str, index: int) -> Dict:
        """Analyze single chord."""
        try:
            # Normalize chord symbol before parsing
            normalized = self._normalize_chord_symbol(symbol)
            c = harmony.ChordSymbol(normalized)
            rn = roman.romanNumeralFromChord(c, self.current_key)

            func = self._get_function(rn)

            # Get jazz-style Roman numeral (not figured bass)
            jazz_roman = self._format_jazz_roman(rn, c, symbol)

            # Check for secondary dominants
            is_secondary = '/' in jazz_roman
            secondary_target = None

            if is_secondary:
                parts = jazz_roman.split('/')
                if len(parts) > 1:
                    secondary_target = parts[1]
                func = 'secondary'

            return {
                "index": index,
                "symbol": symbol,
                "roman": jazz_roman,
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

    def _format_jazz_roman(self, rn, chord, symbol: str) -> str:
        """Format Roman numeral in jazz style (e.g., 'vim7' not 'i#653')."""
        # Get base numeral (I, ii, III, IV, V, vi, vii)
        base = rn.romanNumeral

        # Check for secondary dominant (V/V, V/ii, etc.)
        if rn.secondaryRomanNumeral:
            secondary = rn.secondaryRomanNumeral.romanNumeral
            quality = self._get_quality_suffix(symbol)
            return f"{base}{quality}/{secondary}"

        # Get quality suffix from chord symbol
        quality = self._get_quality_suffix(symbol)

        return f"{base}{quality}"

    def _get_quality_suffix(self, symbol: str) -> str:
        """Extract jazz-style quality suffix from chord symbol."""
        # Remove root note (A-G with optional # or b)
        import re
        match = re.match(r'^[A-G][#b]?(.*)$', symbol)
        if not match:
            return ''

        suffix = match.group(1)

        # Map common chord suffixes to jazz notation
        # Already jazz-style, just clean up
        suffix_map = {
            '': '',           # Major triad
            'M': '',          # Major triad
            'maj': '',        # Major triad
            'm': 'm',         # Minor
            'min': 'm',       # Minor
            '-': 'm',         # Minor (jazz notation)
            '7': '7',         # Dominant 7
            'M7': 'maj7',     # Major 7
            'maj7': 'maj7',   # Major 7
            'Maj7': 'maj7',   # Major 7
            'm7': 'm7',       # Minor 7
            'min7': 'm7',     # Minor 7
            '-7': 'm7',       # Minor 7
            'dim': 'dim',     # Diminished
            'o': 'dim',       # Diminished
            'dim7': 'dim7',   # Diminished 7
            'o7': 'dim7',     # Diminished 7
            'm7b5': 'm7b5',   # Half-diminished
            'ø': 'm7b5',      # Half-diminished
            'ø7': 'm7b5',     # Half-diminished
            '+': 'aug',       # Augmented
            'aug': 'aug',     # Augmented
            '6': '6',         # Major 6
            'm6': 'm6',       # Minor 6
            '9': '9',         # Dominant 9
            'maj9': 'maj9',   # Major 9
            'm9': 'm9',       # Minor 9
            '11': '11',       # 11th
            '13': '13',       # 13th
            'sus4': 'sus4',   # Suspended 4
            'sus2': 'sus2',   # Suspended 2
            'add9': 'add9',   # Add 9
            '7alt': '7alt',   # Altered dominant
            '7#9': '7#9',     # Sharp 9
            '7b9': '7b9',     # Flat 9
        }

        # Try direct mapping first
        if suffix in suffix_map:
            return suffix_map[suffix]

        # Return cleaned suffix as-is if not in map
        return suffix

    def _get_function(self, rn) -> str:
        """Map scale degree to harmonic function."""
        degree = rn.scaleDegree
        if degree in [1, 3, 6]:
            return 'tonic'
        elif degree in [2, 4]:
            return 'subdominant'
        elif degree in [5, 7]:
            return 'dominant'
        return 'chromatic'

    def _detect_patterns(self, chords: List[Dict]) -> List[Dict]:
        """Detect ii-V-I and other common jazz patterns."""
        patterns = []

        for i in range(len(chords) - 2):
            r1 = chords[i]['roman'].lower()
            r2 = chords[i + 1]['roman'].lower()
            r3 = chords[i + 2]['roman'].lower()

            # ii-V-I detection
            if r1.startswith('ii') and r2.startswith('v') and r3.startswith('i'):
                patterns.append({
                    "type": "ii-V-I",
                    "indices": [i, i + 1, i + 2],
                    "description": f"ii-V-I in {chords[i + 2]['key_context']}"
                })

        return patterns


def analyze_song(chords: List[str], key_override: str = None) -> Dict:
    """Main entry point for song analysis."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_progression(chords, key_override)
