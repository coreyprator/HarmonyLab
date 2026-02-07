"""
HarmonyLab Settings - Cloud-First Configuration
Loads secrets from Google Secret Manager (production)
Falls back to environment variables (CI/CD)
"""
import os
from functools import lru_cache
from typing import Optional

# Only import secretmanager if available (not required in CI/CD)
try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False


def get_secret(secret_id: str, project_id: str = "super-flashcards-475210") -> str:
    """
    Fetch secret from Google Secret Manager.
    Falls back to environment variable if Secret Manager unavailable.
    """
    # Environment variable takes precedence (for Cloud Run injection)
    # Check full name first (HARMONYLAB_DB_SERVER), then short name (DB_SERVER)
    env_key = secret_id.upper().replace("-", "_")
    env_value = os.getenv(env_key)
    if env_value:
        return env_value.strip()
    # Check short env var name (strip prefix)
    short_key = env_key.split("_", 1)[-1] if "_" in env_key else env_key
    env_value = os.getenv(short_key)
    if env_value:
        return env_value.strip()
    
    # Try Secret Manager
    if HAS_SECRET_MANAGER:
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            print(f"Warning: Could not fetch secret {secret_id}: {e}")
    
    # Final fallback for local development
    raise ValueError(f"Secret {secret_id} not found in environment or Secret Manager")


class Settings:
    """Application settings loaded from Secret Manager."""
    
    def __init__(self):
        self._project_id = "super-flashcards-475210"
        self._prefix = "harmonylab"
    
    @property
    def db_server(self) -> str:
        return get_secret(f"{self._prefix}-db-server", self._project_id)
    
    @property
    def db_name(self) -> str:
        return get_secret(f"{self._prefix}-db-name", self._project_id)
    
    @property
    def db_user(self) -> str:
        return get_secret(f"{self._prefix}-db-user", self._project_id)
    
    @property
    def db_password(self) -> str:
        return get_secret(f"{self._prefix}-db-password", self._project_id)
    
    @property
    def db_driver(self) -> str:
        # Cloud Run uses Linux driver name
        if os.getenv("K_SERVICE"):  # Cloud Run sets this
            return "ODBC Driver 17 for SQL Server"
        # Local Windows development
        return os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    
    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def environment(self) -> str:
        if os.getenv("K_SERVICE"):
            return "production"
        return os.getenv("ENVIRONMENT", "development")

    @property
    def host(self) -> str:
        return os.getenv("HOST", "0.0.0.0")

    @property
    def api_host(self) -> str:
        return self.host

    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8080"))

    @property
    def api_port(self) -> int:
        return self.port

    @property
    def jwt_secret_key(self) -> str:
        """Secret key for JWT tokens."""
        try:
            return get_secret(f"{self._prefix}-jwt-secret", self._project_id)
        except ValueError:
            # Fallback for local development
            import secrets
            return os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))

    @property
    def google_client_id(self) -> Optional[str]:
        """Google OAuth Client ID."""
        try:
            return get_secret(f"{self._prefix}-google-client-id", self._project_id)
        except ValueError:
            return os.getenv("GOOGLE_CLIENT_ID")

    @property
    def google_client_secret(self) -> Optional[str]:
        """Google OAuth Client Secret."""
        try:
            return get_secret(f"{self._prefix}-google-client-secret", self._project_id)
        except ValueError:
            return os.getenv("GOOGLE_CLIENT_SECRET")

    @property
    def google_redirect_uri(self) -> Optional[str]:
        """Google OAuth redirect URI."""
        if os.getenv("K_SERVICE"):
            return "https://harmonylab-wmrla7fhwa-uc.a.run.app/api/v1/auth/google/callback"
        return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/api/v1/auth/google/callback")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Convenience export
settings = get_settings()

