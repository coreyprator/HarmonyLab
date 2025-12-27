from pydantic_settings import BaseSettings
from typing import List
from google.cloud import secretmanager


def get_secret(secret_id: str, project_id: str = "super-flashcards-475210") -> str:
    """Retrieve a secret from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Warning: Could not retrieve secret '{secret_id}': {e}")
        return ""


class Settings(BaseSettings):
    """Application settings loaded from Google Cloud Secret Manager."""
    
    # GCP Configuration
    gcp_project: str = "super-flashcards-475210"
    
    # Database Configuration
    db_server: str = "35.224.242.223"
    db_name: str = "HarmonyLab"
    db_driver: str = "ODBC Driver 17 for SQL Server"
    
    @property
    def db_user(self) -> str:
        return get_secret("harmonylab-db-user", self.gcp_project)
    
    @property
    def db_password(self) -> str:
        return get_secret("harmonylab-db-password", self.gcp_project)
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Cloud Storage
    gcs_bucket_name: str = ""
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    
    # Environment
    environment: str = "development"
    
    @property
    def database_url(self) -> str:
        """Construct MS SQL connection string."""
        return (
            f"DRIVER={{{self.db_driver}}};"
            f"SERVER={self.db_server};"
            f"DATABASE={self.db_name};"
            f"UID={self.db_user};"
            f"PWD={self.db_password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields for compatibility


# Global settings instance
settings = Settings()
