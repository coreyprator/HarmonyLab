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
