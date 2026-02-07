"""
HarmonyLab Harmonic Analysis Service
Uses music21 for Roman numeral analysis, key detection, and pattern recognition.
"""
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
                except Exception:
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
