from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_JWT_SECRETS = frozenset(
    {
        "change-me-to-a-long-random-secret",
        "secret",
        "changeme",
        "jwt-secret",
        "test-secret-not-for-production-use-only",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ORVIA API"
    app_env: str = "development"
    debug: bool = False

    database_url: str

    jwt_secret: str = Field(repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    auth_password_min_length: int = 10
    auth_login_rate_limit_enabled: bool = True
    auth_login_rate_limit_max_attempts: int = 5
    auth_login_rate_limit_window_seconds: int = 300

    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    invitation_expire_hours: int = 168

    email_provider: str = "logging"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = Field(default=None, repr=False)
    smtp_from: str = "noreply@localhost"
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 15
    notification_max_attempts: int = 3
    notification_retry_backoff_seconds: int = 0
    outbox_worker_enabled: bool = True
    outbox_poll_interval_seconds: float = 5
    outbox_batch_size: int = 50
    outbox_processing_timeout_seconds: int = 300
    outbox_max_attempts: int = 3
    outbox_retry_base_seconds: int = 10

    demo_seed_enabled: bool = False
    demo_seed_email: str | None = None
    demo_seed_password: str | None = Field(default=None, repr=False)
    demo_seed_org_name: str = "ORVIA Demo"

    storage_provider: str = "memory"
    memory_storage_public_base_url: str = "http://127.0.0.1:8000"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = Field(default=None, repr=False)
    s3_secret_access_key: str | None = Field(default=None, repr=False)
    s3_force_path_style: bool = False
    pod_upload_url_ttl_seconds: int = 300
    pod_download_url_ttl_seconds: int = 120
    pod_signature_max_bytes: int = 2_000_000
    pod_photo_max_bytes: int = 8_000_000
    pod_evidence_pending_ttl_seconds: int = 86_400
    pod_evidence_cleanup_enabled: bool = True
    pod_evidence_cleanup_interval_seconds: int = 3_600
    pod_evidence_cleanup_batch_size: int = 100

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_from_address(self) -> str:
        return (self.smtp_from_email or self.smtp_from or "").strip()

    @property
    def is_production(self) -> bool:
        return self.app_env.lower().strip() in {"production", "prod"}

    @model_validator(mode="after")
    def reject_unsafe_production_settings(self):
        if (self.jwt_algorithm or "").upper() == "NONE":
            raise ValueError("JWT_ALGORITHM cannot be none")
        if self.auth_password_min_length < 8:
            raise ValueError("AUTH_PASSWORD_MIN_LENGTH cannot be less than 8")
        if self.auth_login_rate_limit_max_attempts < 1:
            raise ValueError("AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS must be at least 1")
        if self.auth_login_rate_limit_window_seconds < 1:
            raise ValueError("AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS must be at least 1")
        if not self.is_production:
            return self
        if self.demo_seed_enabled:
            raise ValueError("DEMO_SEED_ENABLED cannot be true in production")
        if not (self.database_url or "").strip():
            raise ValueError("DATABASE_URL is required in production")
        secret = (self.jwt_secret or "").strip()
        if len(secret) < 32 or secret.lower() in _WEAK_JWT_SECRETS:
            raise ValueError("JWT_SECRET is too weak for production")
        if self.debug:
            raise ValueError("DEBUG must be false in production")
        origins = [origin.lower() for origin in self.cors_origin_list]
        if not origins:
            raise ValueError("CORS_ORIGINS must be set in production")
        if any(origin in {"*", "null"} for origin in origins):
            raise ValueError("CORS_ORIGINS cannot use a wildcard in production")
        if (self.email_provider or "").lower().strip() != "smtp":
            raise ValueError("EMAIL_PROVIDER must be smtp in production")
        if not (self.smtp_host or "").strip() or not self.smtp_from_address:
            raise ValueError("SMTP_HOST and SMTP_FROM_EMAIL are required in production")
        if (self.storage_provider or "").lower().strip() != "s3":
            raise ValueError("STORAGE_PROVIDER must be s3 in production")
        if not (self.s3_bucket or "").strip():
            raise ValueError("S3_BUCKET is required in production")
        if not (self.s3_access_key_id or "").strip() or not (self.s3_secret_access_key or "").strip():
            raise ValueError("S3 credentials are required in production")
        if self.pod_upload_url_ttl_seconds < 1 or self.pod_download_url_ttl_seconds < 1:
            raise ValueError("POD signed URL TTLs must be positive")
        if self.pod_upload_url_ttl_seconds > 3600 or self.pod_download_url_ttl_seconds > 600:
            raise ValueError("POD signed URL TTLs are too long for production")
        return self


settings = Settings()
