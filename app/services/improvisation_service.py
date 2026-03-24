"""
Improvisation Generation Service (HL-IMPROV-001)
Generates jazz improvisation riffs over a song's chord progression.
Uses RLHF feedback from previous iterations to improve quality.
"""
import json
import logging
import os
from anthropic import Anthropic
from app.db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ImprovisationService:
    """AI jazz improvisation generator with RLHF feedback loop."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or DatabaseConnection()

    def generate_improvisation(self, song_id: int, iteration: int = 1) -> dict:
        """
        Generate jazz improvisation riffs over a song's chord progression.
        Uses RLHF feedback from previous iterations to improve.
        """
        # 1. Get chord progression from cached analysis
        analysis = self.db.execute_query(
            "SELECT analysis_json FROM SongAnalysis WHERE song_id = ?",
            (song_id,)
        )
        if not analysis or not analysis[0].get("analysis_json"):
            raise ValueError(f"No analysis found for song {song_id}. Run analysis first.")

        analysis_data = json.loads(analysis[0]["analysis_json"])
        chords = analysis_data.get("chords", [])
        if not chords:
            raise ValueError(f"No chords found in analysis for song {song_id}.")

        # 2. Get key centers
        key_centers = analysis_data.get("key_centers", [])
        detected_key = analysis_data.get("detected_key", "C")

        # 3. Load approved patterns from knowledge base
        approved_patterns = self.db.execute_query("""
            SELECT pattern_name, chord_context, notes_template,
                   approved_count, rejected_count
            FROM JazzTheoryPatterns
            WHERE approved_count >= rejected_count
            ORDER BY (approved_count - rejected_count) DESC
        """)

        # 4. Get RLHF feedback from previous iterations of this song
        prior_feedback = self.db.execute_query("""
            SELECT r.riff_type, r.pattern_desc, r.rlhf_rating
            FROM ImprovisationRiffs r
            JOIN ImprovisationSessions s ON r.session_id = s.id
            WHERE s.song_id = ? AND r.rlhf_rating IS NOT NULL
            ORDER BY r.rated_at DESC
        """, (song_id,))

        # 5. Get song title for context
        song = self.db.execute_query("SELECT title, composer FROM Songs WHERE id = ?", (song_id,))
        song_title = song[0]["title"] if song else "Unknown"
        song_composer = song[0].get("composer", "") if song else ""

        # 6. Build prompt and call Anthropic API
        prompt = self._build_improv_prompt(
            chords, detected_key, key_centers, approved_patterns,
            prior_feedback, song_title, song_composer, iteration
        )

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        if not client.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        logger.info(f"[IMPROV] Calling Claude API for song {song_id} iteration {iteration}")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_text = response.content[0].text
        logger.info(f"[IMPROV] Claude response length: {len(raw_text)} chars, stop_reason: {response.stop_reason}")
        logger.info(f"[IMPROV] Claude response preview: {raw_text[:300]}")

        riffs = self._parse_improv_response(raw_text)
        logger.info(f"[IMPROV] Parsed {len(riffs)} riffs")

        if not riffs:
            logger.error(f"[IMPROV] No riffs parsed. Full response: {raw_text[:500]}")
            raise ValueError("AI returned no valid riff data.")

        # 7. Store session and riffs
        session_id = self.db.execute_scalar(
            "INSERT INTO ImprovisationSessions (song_id, iteration, status) "
            "OUTPUT INSERTED.id VALUES (?, ?, 'draft')",
            (song_id, iteration)
        )

        for riff in riffs:
            self.db.execute_non_query(
                "INSERT INTO ImprovisationRiffs "
                "(session_id, measure_start, measure_end, riff_type, notes_json, pattern_desc) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    riff.get("measure_start", 1),
                    riff.get("measure_end", 4),
                    riff.get("riff_type", "invented"),
                    json.dumps(riff.get("notes", [])),
                    riff.get("pattern_desc", "")[:200],
                )
            )

        # 8. Return session with riffs
        return self._get_session(session_id)

    def rate_riff(self, riff_id: int, rating: int) -> dict:
        """Rate a riff: -1 (dislike), 0 (neutral), 1 (like)."""
        if rating not in (-1, 0, 1):
            raise ValueError("Rating must be -1, 0, or 1")

        self.db.execute_non_query(
            "UPDATE ImprovisationRiffs SET rlhf_rating = ?, rated_at = GETUTCDATE() WHERE id = ?",
            (rating, riff_id)
        )

        # Update JazzTheoryPatterns approved/rejected counts
        riff = self.db.execute_query(
            "SELECT riff_type FROM ImprovisationRiffs WHERE id = ?", (riff_id,)
        )
        if riff and riff[0].get("riff_type"):
            riff_type = riff[0]["riff_type"]
            if rating == 1:
                self.db.execute_non_query(
                    "UPDATE JazzTheoryPatterns SET approved_count = approved_count + 1 "
                    "WHERE pattern_name LIKE ?", (f"%{riff_type}%",)
                )
            elif rating == -1:
                self.db.execute_non_query(
                    "UPDATE JazzTheoryPatterns SET rejected_count = rejected_count + 1 "
                    "WHERE pattern_name LIKE ?", (f"%{riff_type}%",)
                )

        return self.db.execute_query(
            "SELECT id, rlhf_rating, rated_at FROM ImprovisationRiffs WHERE id = ?",
            (riff_id,)
        )[0]

    def get_session(self, session_id: int) -> dict:
        """Get an improvisation session with riffs."""
        return self._get_session(session_id)

    def get_sessions_for_song(self, song_id: int) -> list:
        """Get all improvisation sessions for a song."""
        sessions = self.db.execute_query(
            "SELECT id, song_id, iteration, status, created_at "
            "FROM ImprovisationSessions WHERE song_id = ? ORDER BY iteration DESC",
            (song_id,)
        )
        for s in sessions:
            s["riffs"] = self.db.execute_query(
                "SELECT id, measure_start, measure_end, riff_type, notes_json, "
                "pattern_desc, rlhf_rating, rated_at "
                "FROM ImprovisationRiffs WHERE session_id = ? ORDER BY measure_start",
                (s["id"],)
            )
            for r in s["riffs"]:
                if r.get("notes_json"):
                    try:
                        r["notes"] = json.loads(r["notes_json"])
                    except (json.JSONDecodeError, TypeError):
                        r["notes"] = []
        return sessions

    def _get_session(self, session_id: int) -> dict:
        """Fetch a single session with its riffs."""
        sessions = self.db.execute_query(
            "SELECT id, song_id, iteration, status, created_at "
            "FROM ImprovisationSessions WHERE id = ?",
            (session_id,)
        )
        if not sessions:
            raise ValueError(f"Session {session_id} not found")
        session = sessions[0]
        session["riffs"] = self.db.execute_query(
            "SELECT id, measure_start, measure_end, riff_type, notes_json, "
            "pattern_desc, rlhf_rating, rated_at "
            "FROM ImprovisationRiffs WHERE session_id = ? ORDER BY measure_start",
            (session_id,)
        )
        for r in session["riffs"]:
            if r.get("notes_json"):
                try:
                    r["notes"] = json.loads(r["notes_json"])
                except (json.JSONDecodeError, TypeError):
                    r["notes"] = []
        return session

    def _build_improv_prompt(
        self, chords, detected_key, key_centers, approved_patterns,
        prior_feedback, song_title, song_composer, iteration
    ) -> str:
        """Build the Claude prompt for improvisation generation."""
        chord_list = "\n".join(
            f"Measure {c.get('measure', i+1)}: {c.get('symbol', c.get('chord_symbol', 'N.C.'))} "
            f"({c.get('roman', c.get('roman_numeral', '?'))})"
            for i, c in enumerate(chords[:32])
        )

        kc_str = ", ".join(
            kc.get("key", kc.get("key_center", "?"))
            for kc in (key_centers if key_centers else [{"key": detected_key}])
        )

        approved = "\n".join(
            f"- {p['pattern_name']} over {p['chord_context']} "
            f"(approved {p.get('approved_count', 0)}x)"
            for p in (approved_patterns or [])[:10]
        )

        liked = "\n".join(
            f"- {f['pattern_desc']} (liked)"
            for f in (prior_feedback or []) if f.get("rlhf_rating") == 1
        )
        avoid = "\n".join(
            f"- {f['pattern_desc']} (disliked)"
            for f in (prior_feedback or []) if f.get("rlhf_rating") == -1
        )

        return f"""You are a jazz improvisation assistant generating melodic ideas for "{song_title}" by {song_composer}.
This is iteration {iteration} of the improvisation.

CHORD PROGRESSION:
{chord_list}

KEY CENTERS: {kc_str}

PREFERRED PATTERNS (use these more):
{approved or 'None yet — use standard bebop vocabulary'}

LIKED IDEAS FROM PRIOR ITERATIONS:
{liked or 'None yet'}

AVOID THESE (user disliked):
{avoid or 'None yet'}

Generate 4-8 improvisation phrases. For each phrase, provide:
1. measure_start and measure_end (integers)
2. riff_type: one of bebop_lick, scale_run, motif, chromatic, arpeggio, enclosure, invented
3. notes: array of objects with pitch (e.g. "C4"), duration (in beats, e.g. 0.5), beat (start beat, e.g. 1.0)
4. pattern_desc: one sentence description of the musical idea

Return ONLY a JSON array of riff objects, no markdown fences, no commentary. Example:
[{{"measure_start":1,"measure_end":2,"riff_type":"bebop_lick","notes":[{{"pitch":"D4","duration":0.5,"beat":1.0}},{{"pitch":"E4","duration":0.5,"beat":1.5}}],"pattern_desc":"Ascending bebop line over Dm7"}}]"""

    def _parse_improv_response(self, text: str) -> list:
        """Parse Claude's JSON response into riff objects. Handles markdown fences and dict wrappers."""
        import re

        # Strip markdown code fences if present
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        # Try direct JSON parse
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and 'riffs' in data:
                return data['riffs']
            logger.warning(f"[IMPROV] AI response is not a JSON array or {{riffs:[]}}: {type(data).__name__}")
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON array from text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"[IMPROV] Could not parse riffs from response: {text[:300]}")
        return []
