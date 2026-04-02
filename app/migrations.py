"""
HarmonyLab Database Migrations
Idempotent schema migrations run at startup.
"""
import logging
from app.db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


def run_migrations():
    """Run all idempotent migrations."""
    db = DatabaseConnection()
    logger.info("Running database migrations...")

    # Migration 1: SongAnalysis table (cached analysis results)
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SongAnalysis'"
        )
        if count == 0:
            logger.info("  Migration 1: Creating SongAnalysis table...")
            db.execute_non_query("""
                CREATE TABLE SongAnalysis (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL,
                    detected_key NVARCHAR(20),
                    manual_key_override NVARCHAR(20),
                    confidence FLOAT,
                    analysis_json NVARCHAR(MAX),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_SongAnalysis_Songs FOREIGN KEY (song_id)
                        REFERENCES Songs(id) ON DELETE CASCADE,
                    CONSTRAINT UQ_SongAnalysis_SongId UNIQUE (song_id)
                )
            """)
            logger.info("  Migration 1: SongAnalysis table created.")
        else:
            logger.info("  Migration 1: SongAnalysis table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 1 warning: {e}")

    # Migration 2: ChordAnalysisOverrides table
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ChordAnalysisOverrides'"
        )
        if count == 0:
            logger.info("  Migration 2: Creating ChordAnalysisOverrides table...")
            db.execute_non_query("""
                CREATE TABLE ChordAnalysisOverrides (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL,
                    chord_index INT NOT NULL,
                    roman_override NVARCHAR(20),
                    function_override NVARCHAR(30),
                    key_context_override NVARCHAR(20),
                    is_pivot_chord BIT DEFAULT 0,
                    pivot_to_key NVARCHAR(20),
                    notes NVARCHAR(500),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_ChordOverrides_Songs FOREIGN KEY (song_id)
                        REFERENCES Songs(id) ON DELETE CASCADE,
                    CONSTRAINT UQ_ChordOverride UNIQUE (song_id, chord_index)
                )
            """)
            logger.info("  Migration 2: ChordAnalysisOverrides table created.")
        else:
            logger.info("  Migration 2: ChordAnalysisOverrides table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 2 warning: {e}")

    # Migration 3: KeyRegions table
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'KeyRegions'"
        )
        if count == 0:
            logger.info("  Migration 3: Creating KeyRegions table...")
            db.execute_non_query("""
                CREATE TABLE KeyRegions (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL,
                    start_chord_index INT NOT NULL,
                    end_chord_index INT,
                    key_center NVARCHAR(20) NOT NULL,
                    transition_type NVARCHAR(30),
                    pivot_chord_index INT,
                    notes NVARCHAR(500),
                    is_user_defined BIT DEFAULT 0,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_KeyRegions_Songs FOREIGN KEY (song_id)
                        REFERENCES Songs(id) ON DELETE CASCADE,
                    CONSTRAINT UQ_KeyRegion UNIQUE (song_id, start_chord_index)
                )
            """)
            logger.info("  Migration 3: KeyRegions table created.")
        else:
            logger.info("  Migration 3: KeyRegions table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 3 warning: {e}")

    # Migration 4: Users table (for authentication)
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Users'"
        )
        if count == 0:
            logger.info("  Migration 4: Creating Users table...")
            db.execute_non_query("""
                CREATE TABLE Users (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    email NVARCHAR(255) NOT NULL UNIQUE,
                    display_name NVARCHAR(255),
                    google_id NVARCHAR(255) UNIQUE,
                    avatar_url NVARCHAR(500),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    last_login_at DATETIME2,
                    is_active BIT DEFAULT 1
                )
            """)
            db.execute_non_query("CREATE INDEX IX_Users_Email ON Users(email)")
            db.execute_non_query("CREATE INDEX IX_Users_GoogleID ON Users(google_id)")
            logger.info("  Migration 4: Users table created.")
        else:
            logger.info("  Migration 4: Users table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 4 warning: {e}")

    # Migration 5: Full note data import tables (HL-REIMPORT)
    _migration_5_note_import_tables(db)

    # Migration 7: RLHF sessions table (HL-006C)
    _migration_7_rlhf_sessions(db)

    # Migration 8: Songs.form_override column (BV-04)
    _migration_8_form_override(db)

    # Migration 9: Songs.section_markers_json column (Group E)
    _migration_9_section_markers(db)

    # Migration 10: Improvisation tables (HL-IMPROV-001)
    _migration_10_improvisation_tables(db)

    # Migration 11: jazz_theory_docs table (HM13-REQ-001)
    _migration_11_jazz_theory_docs(db)

    # Migration 12: AI analysis RLHF columns on JazzTheoryPatterns (HM14 HL-055)
    _migration_12_ai_analysis_columns(db)

    # Migration 13: HarmonicAnalysisExchanges table (HM18)
    _migration_13_harmonic_analysis_exchanges(db)

    # Migration 14: analysis_rules table (REQ-009 / HM30B)
    _migration_14_analysis_rules(db)

    logger.info("Migrations complete.")


def _migration_5_note_import_tables(db):
    """Create tables for full note data import (HL-REIMPORT sprint)."""

    # 5a: song_notes
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_notes'"
        )
        if count == 0:
            logger.info("  Migration 5a: Creating song_notes table...")
            db.execute_non_query("""
                CREATE TABLE song_notes (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    track_num SMALLINT NOT NULL DEFAULT 0,
                    track_name NVARCHAR(100) NULL,
                    voice SMALLINT NOT NULL DEFAULT 1,
                    measure_num INT NOT NULL,
                    beat FLOAT NOT NULL,
                    offset_quarters FLOAT NOT NULL DEFAULT 0,
                    midi_pitch SMALLINT NOT NULL,
                    note_name NVARCHAR(10) NOT NULL,
                    duration_quarters FLOAT NOT NULL,
                    duration_type NVARCHAR(20) NULL,
                    dot_count SMALLINT NOT NULL DEFAULT 0,
                    velocity SMALLINT NOT NULL DEFAULT 64,
                    is_rest BIT NOT NULL DEFAULT 0,
                    is_grace BIT NOT NULL DEFAULT 0,
                    tie_type NVARCHAR(10) NULL,
                    stem_direction NVARCHAR(10) NULL,
                    notehead_type NVARCHAR(30) NULL,
                    fingering NVARCHAR(10) NULL
                )
            """)
            db.execute_non_query("CREATE INDEX ix_song_notes_song_measure ON song_notes(song_id, measure_num, beat)")
            db.execute_non_query("CREATE INDEX ix_song_notes_song_track ON song_notes(song_id, track_num)")
            logger.info("  Migration 5a: song_notes created.")
    except Exception as e:
        logger.warning(f"  Migration 5a warning: {e}")

    # 5b: song_note_articulations
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_note_articulations'"
        )
        if count == 0:
            logger.info("  Migration 5b: Creating song_note_articulations table...")
            db.execute_non_query("""
                CREATE TABLE song_note_articulations (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    note_id BIGINT NOT NULL REFERENCES song_notes(id) ON DELETE CASCADE,
                    articulation NVARCHAR(50) NOT NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5b warning: {e}")

    # 5c: song_lyrics
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_lyrics'"
        )
        if count == 0:
            logger.info("  Migration 5c: Creating song_lyrics table...")
            db.execute_non_query("""
                CREATE TABLE song_lyrics (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    measure_num INT NOT NULL,
                    beat FLOAT NOT NULL,
                    syllable NVARCHAR(500) NOT NULL,
                    syllabic NVARCHAR(10) NULL,
                    verse_num SMALLINT NOT NULL DEFAULT 1
                )
            """)
            db.execute_non_query("CREATE INDEX ix_song_lyrics_song_id ON song_lyrics(song_id)")
    except Exception as e:
        logger.warning(f"  Migration 5c warning: {e}")

    # 5d: song_dynamics
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_dynamics'"
        )
        if count == 0:
            db.execute_non_query("""
                CREATE TABLE song_dynamics (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    track_num SMALLINT NOT NULL DEFAULT 0,
                    measure_num INT NOT NULL,
                    beat FLOAT NOT NULL,
                    dynamic NVARCHAR(20) NOT NULL,
                    velocity SMALLINT NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5d warning: {e}")

    # 5e: song_tempos
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_tempos'"
        )
        if count == 0:
            db.execute_non_query("""
                CREATE TABLE song_tempos (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    measure_num INT NOT NULL,
                    beat FLOAT NOT NULL,
                    bpm FLOAT NOT NULL,
                    text NVARCHAR(100) NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5e warning: {e}")

    # 5f: song_time_signatures
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_time_signatures'"
        )
        if count == 0:
            db.execute_non_query("""
                CREATE TABLE song_time_signatures (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    measure_num INT NOT NULL,
                    numerator SMALLINT NOT NULL,
                    denominator SMALLINT NOT NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5f warning: {e}")

    # 5g: song_key_signatures
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_key_signatures'"
        )
        if count == 0:
            db.execute_non_query("""
                CREATE TABLE song_key_signatures (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    measure_num INT NOT NULL,
                    key_name NVARCHAR(20) NOT NULL,
                    sharps_flats SMALLINT NOT NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5g warning: {e}")

    # 5h: song_text_marks
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_text_marks'"
        )
        if count == 0:
            db.execute_non_query("""
                CREATE TABLE song_text_marks (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    measure_num INT NOT NULL,
                    beat FLOAT NOT NULL,
                    text_type NVARCHAR(30) NOT NULL,
                    content NVARCHAR(500) NOT NULL
                )
            """)
    except Exception as e:
        logger.warning(f"  Migration 5h warning: {e}")

    # 5i: Add new columns to Songs table
    new_cols = [
        ("has_note_data", "BIT NOT NULL DEFAULT 0"),
        ("has_lyrics", "BIT NOT NULL DEFAULT 0"),
        ("import_format", "NVARCHAR(20) NULL"),
        ("track_count", "SMALLINT NULL"),
        ("measure_count", "INT NULL"),
        ("total_notes", "INT NULL"),
        ("raw_xml", "NVARCHAR(MAX) NULL"),
    ]
    for col_name, col_def in new_cols:
        try:
            exists = db.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = 'Songs' AND COLUMN_NAME = ?",
                (col_name,)
            )
            if exists == 0:
                logger.info(f"  Migration 5i: Adding Songs.{col_name}...")
                db.execute_non_query(f"ALTER TABLE Songs ADD {col_name} {col_def}")
        except Exception as e:
            logger.warning(f"  Migration 5i ({col_name}) warning: {e}")

    # ======================================================================
    # Migration 6: song_imports provenance table + Songs.version_number
    # ======================================================================
    logger.info("  Migration 6: song_imports provenance table...")

    # 6a: song_imports table
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'song_imports'"
        )
        if count == 0:
            logger.info("  Migration 6a: Creating song_imports table...")
            db.execute_non_query("""
                CREATE TABLE song_imports (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    song_id INT NULL REFERENCES Songs(id) ON DELETE SET NULL,
                    original_filename NVARCHAR(255) NOT NULL,
                    file_size_bytes BIGINT NULL,
                    file_hash_md5 NVARCHAR(32) NULL,
                    file_hash_sha256 NVARCHAR(64) NULL,
                    fs_created_at DATETIME NULL,
                    fs_modified_at DATETIME NULL,
                    uploaded_at DATETIME NOT NULL DEFAULT GETDATE(),
                    import_format NVARCHAR(10) NULL,
                    parser_version NVARCHAR(20) NULL,
                    import_status NVARCHAR(20) NOT NULL DEFAULT 'pending',
                    note_count_imported INT NULL,
                    lyric_count_imported INT NULL,
                    chord_count_imported INT NULL,
                    import_duration_ms INT NULL,
                    import_error_log NVARCHAR(MAX) NULL,
                    import_warnings NVARCHAR(MAX) NULL,
                    source_path NVARCHAR(500) NULL,
                    version_number INT NOT NULL DEFAULT 1
                )
            """)
            db.execute_non_query("CREATE INDEX ix_si_song_id ON song_imports(song_id)")
            db.execute_non_query("CREATE INDEX ix_si_file_hash ON song_imports(file_hash_md5)")
            db.execute_non_query("CREATE INDEX ix_si_uploaded ON song_imports(uploaded_at DESC)")
    except Exception as e:
        logger.warning(f"  Migration 6a warning: {e}")

    # 6b: Add version_number to Songs
    try:
        exists = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'Songs' AND COLUMN_NAME = 'version_number'"
        )
        if exists == 0:
            logger.info("  Migration 6b: Adding Songs.version_number...")
            db.execute_non_query("ALTER TABLE Songs ADD version_number INT NOT NULL DEFAULT 1")
    except Exception as e:
        logger.warning(f"  Migration 6b warning: {e}")

    # 6c: Add base_title to Songs (for versioning lookups)
    try:
        exists = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'Songs' AND COLUMN_NAME = 'base_title'"
        )
        if exists == 0:
            logger.info("  Migration 6c: Adding Songs.base_title...")
            db.execute_non_query("ALTER TABLE Songs ADD base_title NVARCHAR(200) NULL")
    except Exception as e:
        logger.warning(f"  Migration 6c warning: {e}")


def _migration_7_rlhf_sessions(db):
    """HL-006C: RLHF sessions table for toggle + undo support."""

    # 7a: rlhf_sessions table
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'rlhf_sessions'"
        )
        if count == 0:
            logger.info("  Migration 7a: Creating rlhf_sessions table...")
            db.execute_non_query("""
                CREATE TABLE rlhf_sessions (
                    id NVARCHAR(36) PRIMARY KEY,
                    song_id INT NOT NULL REFERENCES Songs(id) ON DELETE CASCADE,
                    activated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                    activated_by NVARCHAR(100) NOT NULL DEFAULT 'user',
                    overrides_applied INT NOT NULL DEFAULT 0,
                    algorithm_version NVARCHAR(20) NOT NULL DEFAULT '1.1',
                    status NVARCHAR(20) NOT NULL DEFAULT 'active',
                    algorithm_snapshot NVARCHAR(MAX) NULL,
                    reverted_at DATETIME2 NULL
                )
            """)
            db.execute_non_query(
                "CREATE INDEX ix_rlhf_sessions_song ON rlhf_sessions(song_id, status)"
            )
            logger.info("  Migration 7a: rlhf_sessions created.")
        else:
            logger.info("  Migration 7a: rlhf_sessions already exists.")
    except Exception as e:
        logger.warning(f"  Migration 7a warning: {e}")


def _migration_8_form_override(db):
    """BV-04: Add form_override column to Songs for editable form label."""
    try:
        exists = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'Songs' AND COLUMN_NAME = 'form_override'"
        )
        if exists == 0:
            logger.info("  Migration 8: Adding Songs.form_override...")
            db.execute_non_query("ALTER TABLE Songs ADD form_override NVARCHAR(50) NULL")
    except Exception as e:
        logger.warning(f"  Migration 8 warning: {e}")


def _migration_9_section_markers(db):
    """Group E: Add section_markers_json column to Songs for rehearsal mark storage."""
    try:
        exists = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'Songs' AND COLUMN_NAME = 'section_markers_json'"
        )
        if exists == 0:
            logger.info("  Migration 9: Adding Songs.section_markers_json...")
            db.execute_non_query("ALTER TABLE Songs ADD section_markers_json NVARCHAR(MAX) NULL")
    except Exception as e:
        logger.warning(f"  Migration 9 warning: {e}")


def _migration_10_improvisation_tables(db):
    """HL-IMPROV-001: Create ImprovisationSessions, ImprovisationRiffs, JazzTheoryPatterns tables."""
    # ImprovisationSessions
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ImprovisationSessions'"
        )
        if count == 0:
            logger.info("  Migration 10a: Creating ImprovisationSessions table...")
            db.execute_non_query("""
                CREATE TABLE ImprovisationSessions (
                    id              INT IDENTITY(1,1) PRIMARY KEY,
                    song_id         INT NOT NULL,
                    iteration       INT DEFAULT 1,
                    status          NVARCHAR(20) DEFAULT 'draft',
                    created_at      DATETIME2 DEFAULT GETUTCDATE(),
                    CONSTRAINT FK_ImprovSessions_Songs FOREIGN KEY (song_id)
                        REFERENCES Songs(id) ON DELETE CASCADE
                )
            """)
            logger.info("  Migration 10a: ImprovisationSessions table created.")
    except Exception as e:
        logger.warning(f"  Migration 10a warning: {e}")

    # ImprovisationRiffs
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ImprovisationRiffs'"
        )
        if count == 0:
            logger.info("  Migration 10b: Creating ImprovisationRiffs table...")
            db.execute_non_query("""
                CREATE TABLE ImprovisationRiffs (
                    id              INT IDENTITY(1,1) PRIMARY KEY,
                    session_id      INT NOT NULL,
                    measure_start   INT NOT NULL,
                    measure_end     INT NOT NULL,
                    riff_type       NVARCHAR(50),
                    notes_json      NVARCHAR(MAX),
                    pattern_desc    NVARCHAR(200),
                    rlhf_rating     INT NULL,
                    rated_at        DATETIME2 NULL,
                    CONSTRAINT FK_ImprovRiffs_Sessions FOREIGN KEY (session_id)
                        REFERENCES ImprovisationSessions(id) ON DELETE CASCADE
                )
            """)
            logger.info("  Migration 10b: ImprovisationRiffs table created.")
    except Exception as e:
        logger.warning(f"  Migration 10b warning: {e}")

    # JazzTheoryPatterns
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'JazzTheoryPatterns'"
        )
        if count == 0:
            logger.info("  Migration 10c: Creating JazzTheoryPatterns table...")
            db.execute_non_query("""
                CREATE TABLE JazzTheoryPatterns (
                    id              INT IDENTITY(1,1) PRIMARY KEY,
                    pattern_name    NVARCHAR(100),
                    chord_context   NVARCHAR(50),
                    notes_template  NVARCHAR(MAX),
                    approved_count  INT DEFAULT 0,
                    rejected_count  INT DEFAULT 0,
                    created_at      DATETIME2 DEFAULT GETUTCDATE()
                )
            """)
            logger.info("  Migration 10c: JazzTheoryPatterns table created.")

            # Seed with standard bebop patterns
            _seed_jazz_theory_patterns(db)
    except Exception as e:
        logger.warning(f"  Migration 10c warning: {e}")


def _seed_jazz_theory_patterns(db):
    """Seed JazzTheoryPatterns with standard jazz vocabulary."""
    patterns = [
        ("bebop_dominant_scale", "dom7", '["1","2","3","4","5","6","b7","7"]',
         "Bebop dominant scale — adds major 7th passing tone between b7 and octave"),
        ("bebop_major_scale", "maj7", '["1","2","3","4","5","#5","6","7"]',
         "Bebop major scale — adds #5 passing tone for chromatic flow"),
        ("minor_bebop_scale", "min7", '["1","2","b3","3","4","5","6","b7"]',
         "Minor bebop scale — chromatic passing tone between b3 and 3"),
        ("enclosure_pattern", "dom7", '["b2","#7","1"]',
         "Enclosure — approach target note from half step above and below"),
        ("ii_V_I_lick_major", "dom7", '["5","4","3","2","1","7","1"]',
         "Classic ii-V-I resolution lick descending through chord tones"),
        ("cry_me_a_river_turn", "min7", '["1","b3","5","b7","5","b3","1"]',
         "Arpeggio turn — outline the minor 7th chord up and back down"),
        ("chromatic_approach", "dom7", '["#4","5","b7","7","1"]',
         "Chromatic approach to resolution — #4 to 5, b7 to 7 to 1"),
        ("coltrane_pattern", "dom7", '["1","2","3","5","#5","3","2","1"]',
         "Coltrane-inspired digital pattern with augmented passing tone"),
        ("parker_lick", "dom7", '["3","#4","5","6","b7","5","3","1"]',
         "Charlie Parker signature lick — chromatic approach to 5th"),
        ("dorian_run", "min7", '["1","2","b3","4","5","6","b7","1"]',
         "Ascending Dorian scale run — standard minor ii chord vocabulary"),
        ("tritone_sub_approach", "dom7", '["b5","4","3","1"]',
         "Tritone substitution approach — descend from b5 to resolve"),
        ("honeysuckle_rose", "maj7", '["5","#5","6","#5","5","3","1"]',
         "Honeysuckle Rose motif — chromatic neighbor around 5th and 6th"),
    ]
    for name, ctx, template, desc in patterns:
        db.execute_non_query(
            "INSERT INTO JazzTheoryPatterns (pattern_name, chord_context, notes_template) "
            "VALUES (?, ?, ?)",
            (name, ctx, template)
        )
    logger.info(f"  Seeded {len(patterns)} jazz theory patterns.")


def _migration_11_jazz_theory_docs(db):
    """HM13-REQ-001: jazz_theory_docs table for song-context-aware theory chat."""
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'jazz_theory_docs'"
        )
        if count == 0:
            logger.info("  Migration 11: Creating jazz_theory_docs table...")
            db.execute_non_query("""
                CREATE TABLE jazz_theory_docs (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    doc_id NVARCHAR(50) NOT NULL UNIQUE,
                    title NVARCHAR(200) NOT NULL,
                    content_md NVARCHAR(MAX) NOT NULL,
                    tags NVARCHAR(500),
                    version NVARCHAR(20) DEFAULT '1.0',
                    updated_at DATETIME2 DEFAULT GETDATE()
                )
            """)
            logger.info("  Migration 11: jazz_theory_docs table created.")
            _seed_jazz_theory_docs(db)
        else:
            logger.info("  Migration 11: jazz_theory_docs table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 11 warning: {e}")


def _seed_jazz_theory_docs(db):
    """Seed jazz_theory_docs with foundational jazz harmony content."""
    docs = [
        (
            "chord-construction",
            "Chord Construction: 7ths and Extensions",
            """# Chord Construction: 7ths and Extensions

Jazz harmony builds chords in thirds above a root note.

**Seventh chords** (the foundation of jazz):
- **Major 7th (Cmaj7)**: 1-3-5-7. Bright, stable. Used on I and IV chords.
- **Dominant 7th (C7)**: 1-3-5-b7. Tension chord. Wants to resolve down a 5th.
- **Minor 7th (Cm7)**: 1-b3-5-b7. Warm, common on ii and vi chords.
- **Half-diminished (Cm7b5)**: 1-b3-b5-b7. Used on vii in major, ii in minor keys.
- **Diminished 7th (Cdim7)**: 1-b3-b5-bb7. Symmetrical. Every note is a minor 3rd apart.

**Extensions** add color above the 7th:
- **9th**: adds the 2nd an octave up. C9 = 1-3-5-b7-9.
- **11th**: adds the 4th. Cm11 = 1-b3-5-b7-9-11. Common on minor chords.
- **13th**: adds the 6th. C13 = 1-3-5-b7-9-13. Full dominant sound.
- **Altered extensions**: b9, #9, #11, b13 create maximum tension on dominant chords.

**Key principle**: In jazz, every chord is at least a 7th chord. Triads sound incomplete.""",
            "chord construction,seventh chords,extensions,jazz harmony basics"
        ),
        (
            "ii-V-I",
            "The ii-V-I Progression",
            """# The ii-V-I Progression

The most common chord progression in jazz. Appears in virtually every standard.

**In major keys** (key of C):
- ii = Dm7 (minor 7th)
- V = G7 (dominant 7th)
- I = Cmaj7 (major 7th)

**In minor keys** (key of C minor):
- ii = Dm7b5 (half-diminished)
- V = G7b9 (dominant with b9)
- i = Cm7 or CmMaj7

**Why it works**: Each chord's root moves down by a perfect 5th (D→G→C), the strongest resolution in tonal harmony.

**Voice leading**: The guide tones (3rds and 7ths) move by half step:
- Dm7: F (3rd) and C (7th)
- G7: B (3rd, was C) and F (7th, stays)
- Cmaj7: E (3rd, was F) and B (7th, was C... wait, F→E, B stays)

**Spotting ii-V-Is**: Look for any minor 7th chord followed by a dominant 7th a 4th higher, resolving to a chord a 5th below the dominant. They can target major OR minor chords.

**Common variations**: ii-V without resolution (turnaround), extended ii-V-I-vi.""",
            "ii-V-I,voice leading,chord progression,resolution"
        ),
        (
            "tritone-substitution",
            "Tritone Substitution",
            """# Tritone Substitution

Replace any dominant 7th chord with the dominant 7th a tritone (b5) away.

**Example**: G7 → Db7 (both resolve to Cmaj7).

**Why it works**: G7 has guide tones B and F. Db7 has guide tones F and Cb(=B). Same guide tones, reversed roles. The resolution voice leading is identical.

**In a ii-V-I**:
- Original: Dm7 - G7 - Cmaj7
- Tritone sub: Dm7 - Db7 - Cmaj7
- Bass line becomes: D - Db - C (chromatic descent — very smooth)

**Spotting tritone subs**: Any dominant 7th chord whose root is a half step above the next chord's root is likely a tritone sub. Db7→C, Eb7→D, Ab7→G, etc.

**Extended tritone subs**: You can also sub the ii chord. Instead of Dm7-G7, play Abm7-Db7 (the ii-V of the sub key).

**Common in standards**: "Satin Doll," "Girl from Ipanema," and many Jobim tunes use tritone subs extensively.""",
            "tritone substitution,dominant chords,reharmonization,voice leading"
        ),
        (
            "rootless-voicings",
            "Rootless Voicings",
            """# Rootless Voicings

Piano voicings that omit the root (the bass player covers it). Essential for comping in a jazz ensemble.

**Type A voicings** (starting from the 3rd):
- Cmaj7: E-G-B-D (3-5-7-9)
- Dm7: F-A-C-E (3-5-7-9)
- G7: B-D-F-A (3-5-7-9)

**Type B voicings** (starting from the 7th):
- Cmaj7: B-D-E-G (7-9-3-5)
- Dm7: C-E-F-A (7-9-3-5)
- G7: F-A-B-D (7-9-3-5)

**Alternating A and B**: In a ii-V-I, alternate voicing types so your hand stays in the same register:
- Dm7 (Type A): F-A-C-E → G7 (Type B): F-A-B-D → Cmaj7 (Type A): E-G-B-D
- Notice how smooth the voice movement is — most notes move by step or stay.

**Why rootless**: Frees the left hand for bass lines or rhythmic comping. Sounds more sophisticated than root-position chords. Standard practice in trio and larger ensemble playing.

**Range**: Keep voicings between C3 and C5 for best sound. Below C3 gets muddy.""",
            "rootless voicings,piano voicings,comping,voice leading"
        ),
        (
            "chord-scales",
            "Chord-Scale Theory",
            """# Chord-Scale Theory

Each chord implies a scale. Knowing the scale tells you which notes are "safe" to play over that chord.

**Major key chord-scales** (in C major):
- I Cmaj7 → C Ionian (major scale)
- ii Dm7 → D Dorian
- iii Em7 → E Phrygian
- IV Fmaj7 → F Lydian
- V G7 → G Mixolydian
- vi Am7 → A Aeolian (natural minor)
- vii Bm7b5 → B Locrian

**Dominant chord variations**:
- Unaltered V7 → Mixolydian
- V7 with altered tensions → Altered scale (7th mode of melodic minor)
- V7#11 → Lydian dominant (4th mode of melodic minor)
- V7 to minor → Phrygian dominant (5th mode of harmonic minor)

**Minor key chord-scales**:
- i → Dorian (most common in jazz) or Aeolian
- ii° → Locrian #2 (6th mode of melodic minor)
- V7 → Mixolydian b9 b13 or Altered

**Practical tip**: You don't need to think of 7 different scales. In major keys, the notes are all the same — it's the major scale starting from different degrees. Focus on the "avoid notes" (notes that clash with the chord) rather than memorizing separate scales.""",
            "chord scales,modes,improvisation,Dorian,Mixolydian,Lydian"
        ),
        (
            "blues-form",
            "Blues Form and Harmony",
            """# Blues Form and Harmony

The 12-bar blues is a foundational form in jazz.

**Basic blues** (key of Bb):
| Bb7  | Eb7  | Bb7  | Bb7  |
| Eb7  | Eb7  | Bb7  | Bb7  |
| F7   | Eb7  | Bb7  | F7   |

**Jazz blues** (with ii-V substitutions):
| Bb7  | Eb7  | Bb7  | Bdim7   |
| Eb7  | Edim7 | Bb7  | Dm7 G7  |
| Cm7  | F7   | Bb7 G7 | Cm7 F7 |

**Bird blues** (Charlie Parker changes, "Blues for Alice"):
| Fmaj7 | Em7b5 A7 | Dm7 G7 | Cm7 F7 |
| Bb7   | Bbm7 Eb7 | Am7 D7 | Abm7 Db7 |
| Gm7   | C7       | Fmaj7 D7 | Gm7 C7 |

**Key features of jazz blues**:
- Quick IV in bar 2
- Diminished passing chords (bars 4, 6)
- ii-V turnarounds throughout
- The basic I-IV-V skeleton is always present underneath

**Common keys**: Bb, F, C (for horns), G, A (for guitar). Piano players should know blues in all 12 keys.

**Blues scale**: 1-b3-4-b5-5-b7. Works over the entire form regardless of chord changes.""",
            "blues,12-bar blues,jazz blues,form"
        ),
        (
            "rhythm-changes",
            "Rhythm Changes",
            """# Rhythm Changes

Based on Gershwin's "I Got Rhythm." One of the most common jazz forms after the blues.

**32-bar AABA form:**

**A section** (8 bars, key of Bb):
| Bbmaj7 Gm7 | Cm7 F7 | Dm7 Gm7 | Cm7 F7 |
| Fm7 Bb7 | Ebmaj7 Ab7 | Bbmaj7 G7 | Cm7 F7 |

**B section** (bridge, 8 bars):
| D7 | D7 | G7 | G7 |
| C7 | C7 | F7 | F7 |

**Simplification**: The A section is essentially I-vi-ii-V repeated with variations. The bridge is a cycle of dominants (III7-VI7-II7-V7).

**Reharmonization options for A section**:
- Bars 1-2: Bbmaj7 | Bb7 Bdim7 | (chromatic bass)
- Bars 5-6: Use tritone subs: Fm7-Bb7 becomes Fm7-E7
- Tag turnarounds with different ii-Vs each time

**Bridge strategies**:
- Each dominant can be preceded by its ii: Am7-D7, Dm7-G7, Gm7-C7, Cm7-F7
- Coltrane changes over the bridge: substitute with major 3rds cycle

**Standards on rhythm changes**: "Anthropology," "Oleo," "Moose the Mooche," "Cottontail," "Lester Leaps In." Hundreds of bebop heads use this form.""",
            "rhythm changes,AABA form,I Got Rhythm,bebop"
        ),
        (
            "comping-patterns",
            "Jazz Comping Patterns",
            """# Jazz Comping Patterns

Comping = accompanying. How the piano supports the soloist rhythmically and harmonically.

**Basic comping rhythms**:
- **Charleston**: hit on beat 1, hit on the "and" of 2. Rest beats 3-4. Most common.
- **Anticipation**: play the chord an 8th note before the downbeat. Creates forward motion.
- **Syncopated hits**: accent offbeats — the "and" of 1, 2, 3, or 4.
- **Whole notes/half notes**: sometimes less is more. Let the soloist breathe.

**Comping principles**:
1. **Listen first**: React to the soloist. Don't play a predetermined pattern.
2. **Leave space**: Silence is part of comping. Don't fill every beat.
3. **Vary rhythm**: Never repeat the same rhythmic pattern more than 2-3 bars.
4. **Register**: Stay in the middle register (C3-C5). Don't compete with bass (low) or soloist (high).
5. **Dynamics**: Match the soloist's energy. Build and release with them.

**Voice leading in comping**: Move as few notes as possible between chords. Smooth voice leading sounds professional. Jumping voicings sounds amateur.

**Freddie Green style**: Quarter notes on every beat, very quiet. Mostly for guitar but piano can use it behind bass solos.

**McCoy Tyner style**: Quartal voicings (stacked 4ths), strong rhythmic attacks. Works over modal tunes.""",
            "comping,rhythm,piano accompaniment,voicings"
        ),
        (
            "reharmonization",
            "Reharmonization Basics",
            """# Reharmonization Basics

Changing the chords of a tune while keeping the melody. Ranges from subtle to radical.

**Level 1 — Diatonic substitution**:
Replace a chord with one that shares most of its notes.
- Cmaj7 → Em7 (shares E, G, B). iii for I.
- Am7 → Cmaj7 (shares C, E, G). I for vi.
- Fmaj7 → Dm7 (shares D, F, A). ii for IV.

**Level 2 — Secondary dominants**:
Add a V7 before any diatonic chord.
- Before Dm7: add A7 (V of ii)
- Before Am7: add E7 (V of vi)
- Before Fmaj7: add C7 (V of IV)

**Level 3 — ii-V insertion**:
Before any target chord, insert its ii-V.
- Targeting Am7: insert Bm7b5-E7
- Targeting Fmaj7: insert Gm7-C7

**Level 4 — Tritone subs and chromatic approaches**:
- Replace any V7 with its tritone sub
- Create chromatic bass lines: C-B-Bb-A (Cmaj7-B7-Bbmaj7-Am7)

**Level 5 — Coltrane changes**:
Divide a long chord into a cycle of major 3rds:
- Cmaj7 (2 bars) → Cmaj7-Abmaj7-Emaj7-Cmaj7

**Golden rule**: The melody note must be a chord tone or tension of your new chord. If the melody clashes, the reharm doesn't work.""",
            "reharmonization,chord substitution,secondary dominants,arrangement"
        ),
        (
            "ear-training-jazz",
            "Ear Training for Jazz Musicians",
            """# Ear Training for Jazz Musicians

Developing the ear to hear chord qualities, progressions, and voice movement.

**Chord quality recognition**:
- Major 7th: bright, open, "floating." Think first chord of "Misty."
- Dominant 7th: strong, wants to move. Think "blues" sound.
- Minor 7th: warm, mellow. Think "So What" opening chord.
- Half-diminished: dark, unstable. The "longing" sound in minor ii-Vs.
- Diminished 7th: tense, symmetrical. Sounds like old movie villain music.

**Hearing ii-V-Is**:
1. Learn to hear the bass movement: down a 5th, down a 5th.
2. The minor-to-dominant-to-major quality shift is distinctive.
3. Practice: play a ii-V-I in every key. Sing the bass notes.

**Hearing modulations**:
- Key change up a half step: sudden brightness (common in pop, rare in jazz).
- Key change to the relative minor: darkening without disruption.
- Key change via pivot chord: one chord that belongs to both keys.

**Transcription** is the best ear training:
1. Pick a solo you love.
2. Learn it by ear, one phrase at a time.
3. Write it down.
4. Analyze what scales/patterns the soloist used over each chord.

**Daily practice**: Sing intervals, transcribe 4-8 bars, play ii-V-Is in all keys by ear.""",
            "ear training,chord recognition,transcription,intervals"
        ),
        (
            "turnarounds",
            "Jazz Turnarounds",
            """# Jazz Turnarounds

A turnaround is a chord progression (usually 2 bars) at the end of a section that leads back to the top.

**Basic turnaround** (key of C):
| Cmaj7 Am7 | Dm7 G7 |
(I - vi - ii - V)

**Common variations**:
- **Tritone sub**: | Cmaj7 A7 | Dm7 Db7 | (sub G7 with Db7)
- **Chromatic**: | Cmaj7 Eb7 | Dm7 Db7 | (all dominants, chromatic bass)
- **Coltrane**: | Cmaj7 Eb7 | Gbmaj7 A7 | (major 3rds cycle)
- **Backdoor**: | Cmaj7 | Fm7 Bb7 | (bVII7 approach — "backdoor" to I)
- **Tadd Dameron**: | Cmaj7 | Ebmaj7 Abmaj7 Dbmaj7 | (descending major 7ths)
- **Lady Bird**: | Cmaj7 | Ebmaj7 Ab7 Dbmaj7 | (Tadd Dameron variant)

**Where turnarounds appear**:
- Last 2 bars of any AABA section
- End of a 12-bar blues (bars 11-12)
- Intro vamps
- Endings (with ritardando)

**Practice**: Take one standard and play it with 5 different turnarounds. The melody stays the same; only the last 2 bars of harmony change.""",
            "turnarounds,chord progression,reharmonization,form"
        ),
        (
            "modal-jazz",
            "Modal Jazz",
            """# Modal Jazz

Instead of fast-moving chord changes, modal jazz uses one or two chords per section, emphasizing scales (modes) over harmonic motion.

**Origin**: Miles Davis's "Kind of Blue" (1959) — the most influential modal jazz album.

**Key tunes**:
- "So What": Dm7 (16 bars) → Ebm7 (8 bars) → Dm7 (8 bars). Two chords, entire tune.
- "Impressions" (Coltrane): Same form as "So What."
- "Maiden Voyage" (Herbie Hancock): 4 sus chords, 8 bars each.
- "Footprints" (Wayne Shorter): Cm7 based, slow harmonic rhythm.

**How to play over modal tunes**:
1. **Think horizontally**: Build melodies from the scale, not arpeggios.
2. **Use intervals**: 4ths and 5ths sound great. Avoid playing up and down the scale stepwise.
3. **Quartal voicings**: Stack 4ths (e.g., D-G-C-F for Dm7). McCoy Tyner's signature sound.
4. **Pentatonic scales**: Over Dm7, use D minor pentatonic, G minor pentatonic, or A minor pentatonic for different colors.
5. **Rhythmic variety**: With fewer chord changes, rhythm becomes the primary source of interest.

**Contrast with bebop**: Bebop = lots of chords, fast changes, arpeggio-based lines. Modal = few chords, scale-based, space and atmosphere.""",
            "modal jazz,modes,Miles Davis,quartal voicings,pentatonic"
        ),
    ]

    for doc_id, title, content_md, tags in docs:
        db.execute_non_query(
            "INSERT INTO jazz_theory_docs (doc_id, title, content_md, tags) VALUES (?, ?, ?, ?)",
            (doc_id, title, content_md, tags)
        )
    logger.info(f"  Seeded {len(docs)} jazz theory docs.")


def _migration_12_ai_analysis_columns(db):
    """HM14 HL-055: Add RLHF columns to JazzTheoryPatterns for AI harmonic analysis."""
    try:
        # Add key_center column if missing
        col_count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'JazzTheoryPatterns' AND COLUMN_NAME = 'key_center'"
        )
        if col_count == 0:
            logger.info("  Migration 12: Adding AI analysis columns to JazzTheoryPatterns...")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD key_center NVARCHAR(20)")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD chord_sequence NVARCHAR(MAX)")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD description NVARCHAR(MAX)")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD source NVARCHAR(20) DEFAULT 'seed'")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD confidence FLOAT DEFAULT 0.5")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD occurrence_count INT DEFAULT 1")
            db.execute_non_query("ALTER TABLE JazzTheoryPatterns ADD song_id INT")
            logger.info("  Migration 12: AI analysis columns added.")
        else:
            logger.info("  Migration 12: AI analysis columns already exist.")
    except Exception as e:
        logger.warning(f"  Migration 12 warning: {e}")


def _migration_13_harmonic_analysis_exchanges(db):
    """HM18: HarmonicAnalysisExchanges table for AI conversation thread."""
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'HarmonicAnalysisExchanges'"
        )
        if count == 0:
            logger.info("  Migration 13: Creating HarmonicAnalysisExchanges table...")
            db.execute_non_query("""
                CREATE TABLE HarmonicAnalysisExchanges (
                    id            INT IDENTITY(1,1) PRIMARY KEY,
                    song_id       INT NOT NULL,
                    exchange_at   DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                    selected_measures  NVARCHAR(500) NULL,
                    selected_chords    NVARCHAR(2000) NULL,
                    user_comment  NVARCHAR(2000) NULL,
                    ai_analysis   NVARCHAR(MAX) NOT NULL,
                    suggested_key NVARCHAR(100) NULL,
                    pattern_identified NVARCHAR(500) NULL,
                    reasoning_trace    NVARCHAR(MAX) NULL,
                    confidence    NVARCHAR(50) NULL,
                    outcome       NVARCHAR(50) NULL,
                    rejection_reason   NVARCHAR(1000) NULL,
                    prior_exchange_ids NVARCHAR(500) NULL
                )
            """)
            db.execute_non_query(
                "CREATE INDEX IX_HarmonicAnalysisExchanges_SongId "
                "ON HarmonicAnalysisExchanges(song_id, exchange_at DESC)"
            )
            logger.info("  Migration 13: HarmonicAnalysisExchanges table created.")
        else:
            logger.info("  Migration 13: HarmonicAnalysisExchanges table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 13 warning: {e}")


def _migration_14_analysis_rules(db):
    """REQ-009 / HM30B: Editable harmonic analysis rules table."""
    try:
        count = db.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'analysis_rules'"
        )
        if count == 0:
            logger.info("  Migration 14: Creating analysis_rules table...")
            db.execute_non_query("""
                CREATE TABLE analysis_rules (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    rule_order INT NOT NULL DEFAULT 0,
                    category NVARCHAR(50) NOT NULL,
                    title NVARCHAR(200) NOT NULL,
                    rule_text NVARCHAR(MAX) NOT NULL,
                    active BIT DEFAULT 1,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
            """)
            logger.info("  Migration 14: analysis_rules table created.")
            _seed_analysis_rules(db)
        else:
            logger.info("  Migration 14: analysis_rules table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 14 warning: {e}")


def _seed_analysis_rules(db):
    """Seed initial analysis rules from Darren session feedback."""
    rules = [
        (1, 'key_center', 'Find all ii-V progressions first',
         'The first step in harmonic analysis is to identify all ii-V progressions. These are the strongest indicators of key center.'),
        (2, 'key_center', 'Look for root movements by circle of 5ths',
         'Trace the root movement of chords around the circle of 5ths. Consistent movement by 5ths indicates a key center.'),
        (3, 'key_center', 'Minor to dominant = same family clue',
         'If you see a minor chord moving to a dominant chord, they are likely in the same harmonic family. The dominant resolves to the tonic, revealing the key center.'),
        (4, 'pattern', 'iii-vi-ii-V is a turnaround',
         'The progression iii-vi-ii-V is a turnaround. If vi is minor (not dominant), the turnaround is in harmonic minor context.'),
    ]
    for order, cat, title, text in rules:
        db.execute_non_query(
            "INSERT INTO analysis_rules (rule_order, category, title, rule_text) VALUES (?, ?, ?, ?)",
            (order, cat, title, text)
        )
    logger.info(f"  Seeded {len(rules)} analysis rules.")
