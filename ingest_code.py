"""
Ingest source code files into MetaPM code_files table.
Usage: python scripts/ingest_code.py --app metapm --repo-root . --sha abc1234

MP102 BUG-208: Uses `git ls-files` to enumerate only git-tracked files.
This makes the file set deterministic regardless of trigger path (local,
CI, deploy-event). A local run with untracked files now produces the same
count as a clean CI checkout. Same deploy_sha always yields the same files.

Connection uses DB_PASSWORD env var or Secret Manager fallback.
"""

import argparse
import os
import subprocess
import sys

# pymssql may not be available in all environments
try:
    import pymssql
except ImportError:
    print("ERROR: pymssql not installed. Run: pip install pymssql")
    sys.exit(1)

# Extensions to include (MP102: explicit allowlist instead of blocklist)
INCLUDED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".sql", ".yaml", ".yml",
    ".json", ".md", ".sh", ".toml", ".cfg", ".ini", ".txt", ".css",
}

# Individual files to exclude (files that cause false positives in static analysis gates)
EXCLUDED_FILES = {
    "app/core/migrations.py",  # MP101: contains ALTER TABLE DDL strings
}

# Path prefixes to exclude (any tracked file under these dirs is skipped)
EXCLUDED_PATH_PREFIXES = (
    "app/migrations/",   # Migration SQL files trigger column_drop_orphans gate
    "incoming_zip/",     # Not source code
    "uat/",              # Not source code
    "docs/",             # Not source code
    "scripts/migrations/",  # Migration helper scripts
)

MAX_FILE_SIZE = 1_000_000  # 1 MB


def list_tracked_files(repo_root: str) -> list[str]:
    """Return git-tracked file paths relative to repo_root.

    MP102 BUG-208: Uses `git ls-files` so the file set is deterministic
    regardless of where the script runs (local, CI, deploy-event).
    Untracked/ignored files are never included.

    Falls back to os.walk + exclusion rules if git ls-files returns 0 files
    (which would indicate a corrupted/empty index rather than a truly empty repo).
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--full-name"],
            capture_output=True, text=True, cwd=repo_root, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"git ls-files failed: {result.stderr.strip()[:200]}")
        paths = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        if paths:
            return paths
        # 0 files from git ls-files but files exist — index likely cleared; fall back
        print("  WARN: git ls-files returned 0 files; falling back to os.walk (index may be cleared)")
    except FileNotFoundError:
        print("  WARN: git not available; falling back to os.walk")
    except Exception as e:
        print(f"  WARN: git ls-files failed ({e}); falling back to os.walk")

    # Fallback: os.walk with exclusion rules (same as MP101 approach)
    _EXCL_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", ".next",
                  ".venv", "venv", "env", "site-packages", "migrations",
                  "incoming_zip", "uat", "docs"}
    _EXCL_FILES = {"app/core/migrations.py"}
    paths = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _EXCL_DIRS]
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, repo_root).replace("\\", "/")
            if rel not in _EXCL_FILES:
                paths.append(rel)
    return paths


def get_connection(db_host: str, db_password: str, database: str = "MetaPM"):
    """Create DB connection via pymssql (no ODBC driver required)."""
    conn = pymssql.connect(
        server=db_host,
        port=1433,
        user="sqlserver",
        password=db_password,
        database=database,
        timeout=30,
        login_timeout=30,
        tds_version="7.4",
    )
    return conn


def ensure_ingestion_runs(conn, app: str, sha: str, trigger_src: str = "cloudbuild") -> str:
    """Insert a 'started' row into ingestion_runs; return its id (MP101 BUG-206)."""
    import uuid as _uuid
    run_id = str(_uuid.uuid4())
    cursor = conn.cursor()
    try:
        cursor.execute("""
            IF NOT EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'ingestion_runs'
            )
            BEGIN
                CREATE TABLE ingestion_runs (
                    id           NVARCHAR(36)  PRIMARY KEY,
                    app          NVARCHAR(64)  NOT NULL,
                    deploy_sha   NVARCHAR(64)  NULL,
                    status       NVARCHAR(20)  NOT NULL DEFAULT 'started',
                    file_count   INT           NULL,
                    started_at   DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
                    completed_at DATETIME2     NULL,
                    error_msg    NVARCHAR(MAX) NULL,
                    trigger_src  NVARCHAR(50)  NULL
                )
            END
        """)
        conn.commit()
        cursor.execute(
            "INSERT INTO ingestion_runs (id, app, deploy_sha, status, trigger_src) VALUES (%s, %s, %s, 'started', %s)",
            (run_id, app, sha, trigger_src)
        )
        conn.commit()
    except Exception as e:
        print(f"  WARN: ingestion_runs tracking failed (non-fatal): {e}")
        run_id = None
    cursor.close()
    return run_id


def record_ingestion_terminal(conn, run_id: str, status: str, file_count: int, error_msg: str = "") -> None:
    """Update ingestion_runs row to terminal status (MP101 BUG-206)."""
    if not run_id:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ingestion_runs
            SET status = %s, file_count = %s, completed_at = SYSUTCDATETIME(), error_msg = %s
            WHERE id = %s
        """, (status, file_count, error_msg or None, run_id))
        conn.commit()
    except Exception as e:
        print(f"  WARN: ingestion_runs terminal update failed (non-fatal): {e}")
    cursor.close()


def ingest(app: str, repo_root: str, sha: str, db_host: str, db_password: str,
           trigger_src: str = "cloudbuild", force: bool = False):
    """Ingest git-tracked source files into code_files.

    MP102 BUG-208: Uses git ls-files for deterministic file enumeration.
    Idempotency guard skips ingestion if a success row already exists for
    this (app, deploy_sha) combination (unless --force is passed).
    """
    repo_root = os.path.abspath(repo_root)
    conn = get_connection(db_host, db_password)

    # MP102: Idempotency guard — skip if already ingested successfully for this sha
    if not force and sha and sha != "unknown":
        cursor_check = conn.cursor()
        try:
            cursor_check.execute(
                "SELECT id FROM ingestion_runs WHERE app = %s AND deploy_sha = %s AND status = 'success'",
                (app, sha)
            )
            existing = cursor_check.fetchone()
            cursor_check.close()
            if existing:
                print(f"  IDEMPOTENT SKIP: {app} sha={sha[:8]} already ingested successfully")
                conn.close()
                return
        except Exception as e:
            cursor_check.close()
            print(f"  WARN: idempotency check failed (non-fatal): {e}")

    run_id = ensure_ingestion_runs(conn, app, sha, trigger_src)
    cursor = conn.cursor()

    ingested = 0
    skipped_large = 0
    seen_paths = set()

    try:
        # MP102 BUG-208: enumerate only git-tracked files for determinism
        tracked_files = list_tracked_files(repo_root)
        print(f"  git ls-files: {len(tracked_files)} tracked files")

        for rel_path in tracked_files:
            rel_path = rel_path.replace("\\", "/")

            # Skip individually excluded files
            if rel_path in EXCLUDED_FILES:
                continue

            # Skip files under excluded path prefixes
            if any(rel_path.startswith(p) for p in EXCLUDED_PATH_PREFIXES):
                continue

            # Extension filter (allowlist)
            ext = os.path.splitext(rel_path)[1].lower()
            if ext not in INCLUDED_EXTENSIONS:
                continue

            full_path = os.path.join(repo_root, rel_path)
            if not os.path.isfile(full_path):
                continue

            file_size = os.path.getsize(full_path)
            if file_size > MAX_FILE_SIZE:
                skipped_large += 1
                print(f"  SKIP (too large): {rel_path} ({file_size:,} bytes)")
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Skip binary files
                if '\x00' in content or content.count('\ufffd') > len(content) * 0.05:
                    continue
            except Exception as e:
                print(f"  SKIP (read error): {rel_path}: {e}")
                continue

            seen_paths.add(rel_path)

            # MERGE (upsert) on (app, file_path)
            cursor.execute("""
                MERGE code_files AS target
                USING (SELECT %s AS app, %s AS file_path) AS source
                ON target.app = source.app AND target.file_path = source.file_path
                WHEN MATCHED THEN
                    UPDATE SET content = %s, file_size = %s, ingested_at = GETUTCDATE(), deploy_sha = %s
                WHEN NOT MATCHED THEN
                    INSERT (app, file_path, content, file_size, deploy_sha)
                    VALUES (%s, %s, %s, %s, %s);
            """, (
                app, rel_path,
                content, file_size, sha,
                app, rel_path, content, file_size, sha,
            ))

            if cursor.rowcount > 0:
                ingested += 1

        conn.commit()

        # Delete stale rows (files no longer tracked in this SHA)
        if seen_paths:
            placeholders = ",".join(["%s" for _ in seen_paths])
            cursor.execute(
                f"DELETE FROM code_files WHERE app = %s AND file_path NOT IN ({placeholders})",
                (app, *sorted(seen_paths)),
            )
            deleted = cursor.rowcount
        else:
            cursor.execute("DELETE FROM code_files WHERE app = %s", (app,))
            deleted = cursor.rowcount

        conn.commit()

        print(f"Ingested {ingested}, deleted {deleted} stale, skipped {skipped_large} (too large)")
        print(f"Total: {len(seen_paths)} files")

        record_ingestion_terminal(conn, run_id, "success", len(seen_paths))
        conn.close()

    except Exception as e:
        print(f"ERROR: ingest failed: {e}")
        try:
            record_ingestion_terminal(conn, run_id, "failure", ingested, str(e)[:500])
            conn.close()
        except Exception:
            pass
        raise



def main():
    parser = argparse.ArgumentParser(description="Ingest source code into MetaPM code_files table")
    parser.add_argument("--app", required=True, help="App name (e.g. metapm, efg, artforge)")
    parser.add_argument("--repo-root", required=True, help="Path to repo root")
    parser.add_argument("--sha", default="unknown", help="Git commit SHA")
    parser.add_argument("--trigger-src", default="cloudbuild", help="Trigger source for ingestion_runs tracking")
    parser.add_argument("--force", action="store_true", help="MP102: Bypass idempotency guard and re-ingest even if success row exists")
    args = parser.parse_args()

    db_host = os.environ.get("DB_HOST", "35.224.242.223")
    db_password = os.environ.get("DB_PASSWORD", "")

    if not db_password:
        # Try Secret Manager fallback
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = "projects/super-flashcards-475210/secrets/db-password/versions/latest"
            response = client.access_secret_version(request={"name": name})
            db_password = response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            print(f"ERROR: No DB_PASSWORD env var and Secret Manager failed: {e}")
            sys.exit(1)

    ingest(args.app, args.repo_root, args.sha, db_host, db_password,
           trigger_src=args.trigger_src, force=args.force)


if __name__ == "__main__":
    main()
