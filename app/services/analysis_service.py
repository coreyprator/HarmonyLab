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

    def analyze_progression(self, chords: List[str], key_override: str = None,
                             midi_notes: List[int] = None,
                             note_measures: List[int] = None,
                             total_measures: int = 0) -> Dict:
        """Analyze full chord progression.

        Args:
            chords: List of chord symbols.
            key_override: Manual key override string.
            midi_notes: Optional list of MIDI pitch values from song_notes.
                        When provided, used for key detection instead of chords
                        (more accurate for imported scores).
            note_measures: Optional list of measure numbers corresponding to midi_notes.
            total_measures: Total measure count for cadence weighting.
        """

        # Detect or use override key
        if key_override:
            self.current_key = key.Key(key_override)
            confidence = 1.0
        elif midi_notes:
            self.current_key, confidence = self._detect_key_from_notes(
                midi_notes, note_measures, total_measures)
        else:
            self.current_key, confidence = self._detect_key(chords)

        # HM14 BUG-2: Resolve relative major/minor ambiguity via last-chord tiebreaker
        self.current_key = self._resolve_relative_ambiguity(self.current_key, chords)

        # Analyze each chord
        analyzed = []
        for i, symbol in enumerate(chords):
            analysis = self._analyze_chord(symbol, i)
            analyzed.append(analysis)

        # HL-006 Item 4a: Secondary dominant detection pass
        # If a dom7 chord is a P5 above the next chord, label it V7/V-style
        analyzed = self._detect_secondary_dominants(analyzed)

        # Detect patterns
        patterns = self._detect_patterns(analyzed)

        return {
            "detected_key": str(self.current_key),
            "confidence": confidence,
            "chords": analyzed,
            "patterns": patterns
        }

    # Dominant 7th interval set (mod 12): root, M3, P5, m7
    _DOM7_INTERVALS = {0, 4, 7, 10}

    def _detect_secondary_dominants(self, analyzed: list) -> list:
        """HL-006 Item 4a: Post-process chords to detect secondary dominants.

        Rule: if chord[n] is a dom7 chord and chord[n+1] resolves by P5 down
        (i.e., chord[n] is a P5 above chord[n+1]), flag chord[n] as a
        potential secondary dominant. Store in 'secondary_dominant_candidate'
        field so the frontend can offer a toggle.
        """
        from music21 import harmony, interval as m21interval, pitch as m21pitch
        import re

        def get_root_semitone(symbol: str) -> int | None:
            """Return root note as semitone (0=C ... 11=B), or None."""
            _NOTE_SEMI = {
                'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
                'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
                'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
            }
            m = re.match(r'^([A-G][#b]?)', symbol or '')
            if not m:
                return None
            return _NOTE_SEMI.get(m.group(1))

        def is_dom7_quality(symbol: str) -> bool:
            """True if symbol appears to be a dominant 7th (X7, X9, X13 etc)."""
            if not symbol:
                return False
            quality = re.sub(r'^[A-G][#b]?', '', symbol)
            # dom7 indicators: bare '7', '7b9', '7#9', '9', '13', '7alt', '7sus4'
            # Exclude maj7, m7, dim7, mMaj7
            if re.match(r'^(7|7b9|7#9|7#11|9|13|7alt|7sus4|9sus4)$', quality):
                return True
            return False

        for i, ch in enumerate(analyzed):
            sym = ch.get('symbol', '')
            if not is_dom7_quality(sym):
                continue
            # All dom7 chords are secondary dominant candidates — show the toggle
            ch['secondary_dominant_candidate'] = True
            # Detect P5 target (next chord that this resolves to)
            if i < len(analyzed) - 1:
                nxt_sym = analyzed[i + 1].get('symbol', '')
                root = get_root_semitone(sym)
                nxt_root = get_root_semitone(nxt_sym)
                if root is not None and nxt_root is not None:
                    if (root - nxt_root) % 12 == 7:
                        ch['secondary_dominant_target'] = nxt_sym

        # HL-044: Detect tritone substitutions and diminished passing chords
        analyzed = self._detect_transition_chords(analyzed)

        return analyzed

    def _detect_transition_chords(self, analyzed: list) -> list:
        """HL-044: Detect tritone substitutions and diminished passing chords.

        Tritone sub: dom7 chord whose root is a tritone (6 semitones) from the
        next chord's root, substituting for V7 of that chord.
        Diminished passing: dim/dim7 chord whose root is a half-step below or
        above the next chord's root (chromatic passing function).
        """
        import re

        def get_root_semitone(symbol: str):
            _NOTE_SEMI = {
                'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
                'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
                'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
            }
            m = re.match(r'^([A-G][#b]?)', symbol or '')
            if not m:
                return None
            return _NOTE_SEMI.get(m.group(1))

        def is_dom7_quality(symbol: str) -> bool:
            if not symbol:
                return False
            quality = re.sub(r'^[A-G][#b]?', '', symbol)
            return bool(re.match(r'^(7|7b9|7#9|7#11|9|13|7alt|7sus4|9sus4)$', quality))

        def is_dim_quality(symbol: str) -> bool:
            if not symbol:
                return False
            quality = re.sub(r'^[A-G][#b]?', '', symbol)
            return bool(re.match(r'^(dim|dim7|o|o7|07|°|°7)$', quality))

        for i, ch in enumerate(analyzed):
            sym = ch.get('symbol', '')
            if i >= len(analyzed) - 1:
                continue
            nxt_sym = analyzed[i + 1].get('symbol', '')
            root = get_root_semitone(sym)
            nxt_root = get_root_semitone(nxt_sym)
            if root is None or nxt_root is None:
                continue

            interval = (root - nxt_root) % 12

            # Tritone substitution: dom7 resolving down a half-step (tritone = 6 semitones from V)
            if is_dom7_quality(sym) and interval == 1:
                # This is a tritone sub if the "real" V would be 7 semitones above next root
                # SubV root is 6 semitones from the "real" V root
                ch['transition_type'] = 'tritone_sub'
                ch['transition_label'] = f'SubV7/{nxt_sym.split("/")[0]}'

            # Diminished passing chord: dim/dim7 a half-step below or above next chord
            if is_dim_quality(sym):
                if interval == 1:  # half-step above → descending passing
                    ch['transition_type'] = 'dim_passing'
                    ch['transition_label'] = f'dim pass → {nxt_sym.split("/")[0]}'
                elif interval == 11:  # half-step below → ascending passing
                    ch['transition_type'] = 'dim_passing'
                    ch['transition_label'] = f'dim pass → {nxt_sym.split("/")[0]}'

        return analyzed

    def _detect_key(self, chords: List[str]) -> tuple:
        """Auto-detect key from chords."""
        try:
            s = stream.Stream()
            added = 0
            for symbol in chords:
                if added >= 16:
                    break
                try:
                    normalized = self._normalize_chord_symbol(symbol)
                    if not normalized:
                        continue
                    cs = harmony.ChordSymbol(normalized)
                    # Convert to plain Chord — ChordSymbol objects confuse
                    # the Krumhansl-Schmuckler algorithm in music21.
                    c = chord.Chord(cs.pitches)
                    s.append(c)
                    added += 1
                except Exception:
                    continue

            if added == 0:
                logger.warning("No valid chords for key detection")
                return key.Key('C'), 0.0

            detected = s.analyze('key')
            conf = getattr(detected, 'correlationCoefficient', 0.5)
            return detected, conf
        except Exception as e:
            logger.warning(f"Key detection failed: {e}")
            return key.Key('C'), 0.0

    def _detect_key_from_notes(self, midi_notes: List[int],
                               note_measures: List[int] = None,
                               total_measures: int = 0) -> tuple:
        """Detect key from MIDI pitch values using Krumhansl-Schmuckler.

        HL-006A Change 5: Cadence weighting — notes in last 4 measures
        get 3x weight, root of final chord gets additional 2x.
        """
        try:
            from music21 import note as m21note, duration as m21dur
            s = stream.Stream()

            # Determine cadence zone (last 4 measures)
            max_measure = total_measures
            if note_measures:
                max_measure = max(max_measure, max(note_measures))
            cadence_start = max(1, max_measure - 3)

            for i, midi_pitch in enumerate(midi_notes[:200]):
                try:
                    n = m21note.Note(midi_pitch)
                    # HL-006A Change 5: Cadence weighting
                    if note_measures and i < len(note_measures):
                        m = note_measures[i]
                        if m >= cadence_start:
                            # 3x weight for last 4 measures (use longer duration as proxy)
                            n.duration = m21dur.Duration(3.0)
                            # Extra weight for very last measure
                            if m == max_measure:
                                n.duration = m21dur.Duration(6.0)
                    s.append(n)
                except Exception:
                    continue

            if len(s) == 0:
                logger.warning("No valid notes for key detection")
                return key.Key('C'), 0.0

            detected = s.analyze('key')
            conf = getattr(detected, 'correlationCoefficient', 0.5)
            return detected, conf
        except Exception as e:
            logger.warning(f"Key detection from notes failed: {e}")
            return key.Key('C'), 0.0

    # HM14 BUG-2: Relative major/minor tiebreaker using last-measure chords
    RELATIVE_PAIRS = {
        'A minor': 'C major', 'E minor': 'G major', 'D minor': 'F major',
        'B minor': 'D major', 'G minor': 'B- major', 'C minor': 'E- major',
        'F minor': 'A- major', 'F# minor': 'A major', 'C# minor': 'E major',
        'G# minor': 'B major', 'B- minor': 'D- major', 'E- minor': 'G- major',
    }

    def _resolve_relative_ambiguity(self, detected_key, chords: List[str]) -> object:
        """If detected key is minor, check if its relative major is a better fit
        based on the last chord of the song (jazz standard final cadence rule)."""
        key_str = str(detected_key)
        if key_str not in self.RELATIVE_PAIRS:
            return detected_key

        relative_major_str = self.RELATIVE_PAIRS[key_str]
        major_tonic = relative_major_str.split()[0]

        # Check last non-empty chord
        last_chord = None
        for c in reversed(chords):
            if c and c != 'N.C.':
                last_chord = c
                break

        if not last_chord:
            return detected_key

        # Extract root of last chord
        import re
        match = re.match(r'^([A-G])([#b]?)', last_chord)
        if not match:
            return detected_key

        last_root = match.group(1) + match.group(2)

        # Normalize for comparison (B- = Bb, E- = Eb, etc.)
        normalize = {'B-': 'Bb', 'E-': 'Eb', 'A-': 'Ab', 'D-': 'Db', 'G-': 'Gb'}
        major_tonic_norm = normalize.get(major_tonic, major_tonic)

        if last_root == major_tonic_norm:
            logger.info(f"[KEY-DETECT] Relative ambiguity resolved: {key_str} → {relative_major_str} (last chord root: {last_root})")
            return key.Key(major_tonic_norm)

        return detected_key

    def _normalize_chord_symbol(self, symbol: str) -> str:
        """Normalize chord symbols for music21 parsing.

        Handles standard notation, MuseScore jazz font shorthand, flat notation,
        and parenthetical extensions like (b5), (#9), (b9).
        MuseScore jazz font uses: ^=maj, -=minor, 0=dim, t/triangle=maj7
        """
        import re

        if not symbol or symbol == 'N.C.':
            return ''

        # Extract root (A-G with optional # or b) and quality
        root_match = re.match(r'^([A-G][#b]?)(.*)', symbol)
        if not root_match:
            return symbol
        root_part = root_match.group(1)
        quality = root_match.group(2)

        # Convert flat 'b' in root to '-' for music21
        if len(root_part) == 2 and root_part[1] == 'b':
            root_part = root_part[0] + '-'

        # Strip parentheses from extensions: (b5) → b5, (#9) → #9
        quality = re.sub(r'\(([^)]+)\)', r'\1', quality)

        # Normalize MuseScore jazz shorthand quality
        quality = re.sub(r'^\^', 'maj', quality)       # ^7 → maj7, ^9 → maj9
        quality = re.sub(r'^-', 'm', quality)           # -7 → m7, -9 → m9
        quality = re.sub(r'^0(\d)', r'dim\1', quality)  # 07 → dim7
        quality = re.sub(r'^o(\d)', r'dim\1', quality)  # o7 → dim7
        if quality in ('t', '\u0394'):                   # triangle = maj7
            quality = 'maj7'
        if quality == '6/9':
            quality = '69'

        # Handle "Maj" suffix (without number) - remove it
        if quality == 'Maj':
            quality = ''

        return root_part + quality

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
            # Fallback: derive Roman numeral from root note alone
            fallback_roman = self._fallback_roman(symbol)
            func = "unknown"
            if fallback_roman != "?":
                func = "chromatic"  # Best guess when quality unknown
            return {
                "index": index,
                "symbol": symbol,
                "roman": fallback_roman,
                "function": func,
                "color": self.FUNCTION_COLORS.get(func, self.FUNCTION_COLORS['unknown']),
                "key_context": str(self.current_key),
                "is_secondary": False,
                "secondary_target": None
            }

    def _fallback_roman(self, symbol: str) -> str:
        """Derive Roman numeral from root note alone when music21 can't parse."""
        import re
        from music21 import pitch

        root_match = re.match(r'^([A-G][#b]?)', symbol)
        if not root_match or not self.current_key:
            return "?"

        try:
            root_str = root_match.group(1)
            # Convert 'b' to '-' for music21 pitch
            if len(root_str) == 2 and root_str[1] == 'b':
                root_str = root_str[0] + '-'
            root_p = pitch.Pitch(root_str)
            tonic_p = self.current_key.tonic

            interval = (root_p.midi - tonic_p.midi) % 12

            # Determine if minor from symbol
            quality = symbol[len(root_match.group(1)):]
            is_minor = quality.startswith('m') and not quality.startswith('maj')
            is_dim = 'dim' in quality or quality.startswith('ø') or 'b5' in quality

            # Map semitones to scale degrees (major key reference)
            degree_map = {0: 'I', 1: 'bII', 2: 'II', 3: 'bIII', 4: 'III', 5: 'IV',
                          6: '#IV', 7: 'V', 8: 'bVI', 9: 'VI', 10: 'bVII', 11: 'VII'}
            base = degree_map.get(interval, '?')
            if base == '?':
                return '?'

            # Lowercase for minor/diminished
            if is_minor or is_dim:
                base = base.lower()

            # Append quality suffix
            qual_suffix = self._get_quality_suffix(symbol)
            return base + qual_suffix

        except Exception:
            return "?"

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
            '^7': 'maj7',     # Jazz font maj7
            'm7': 'm7',       # Minor 7
            'min7': 'm7',     # Minor 7
            '-7': 'm7',       # Minor 7
            'dim': 'dim',     # Diminished
            'o': 'dim',       # Diminished
            'dim7': 'dim7',   # Diminished 7
            'o7': 'dim7',     # Diminished 7
            '07': 'dim7',     # Jazz font dim7
            'm7b5': 'm7b5',   # Half-diminished
            'ø': 'm7b5',      # Half-diminished
            'ø7': 'm7b5',     # Half-diminished
            '+': 'aug',       # Augmented
            'aug': 'aug',     # Augmented
            '6': '6',         # Major 6
            'm6': 'm6',       # Minor 6
            '9': '9',         # Dominant 9
            'maj9': 'maj9',   # Major 9
            '^9': 'maj9',     # Jazz font maj9
            'm9': 'm9',       # Minor 9
            '-9': 'm9',       # Jazz font m9
            '11': '11',       # 11th
            '13': '13',       # 13th
            'sus4': 'sus4',   # Suspended 4
            'sus2': 'sus2',   # Suspended 2
            'add9': 'add9',   # Add 9
            '7alt': '7alt',   # Altered dominant
            '7#9': '7#9',     # Sharp 9
            '7b9': '7b9',     # Flat 9
            '7#5': '7#5',     # Augmented dom 7
            '7b5': '7b5',     # Flat 5 dom 7
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


def analyze_song(chords: List[str], key_override: str = None,
                  midi_notes: List[int] = None,
                  note_measures: List[int] = None,
                  total_measures: int = 0) -> Dict:
    """Main entry point for song analysis."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_progression(
        chords, key_override, midi_notes, note_measures, total_measures)
