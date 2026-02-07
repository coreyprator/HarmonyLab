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

    logger.info("Migrations complete.")
