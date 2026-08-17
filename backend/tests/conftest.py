import os
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Isolated test DB — NEVER truncate the app database (`orvia`).
# Override with TEST_DATABASE_URL if needed. Set TEST_ALLOW_APP_DB=1 only for
# intentional destructive runs against the app DB (not recommended).
_DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://orvia:orvia@localhost:5433/orvia_test"
_TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DATABASE_URL)
_db_name = (urlparse(_TEST_DATABASE_URL.replace("postgresql+psycopg", "postgresql", 1)).path or "").lstrip("/")
if _db_name == "orvia" and os.environ.get("TEST_ALLOW_APP_DB") != "1":
    raise RuntimeError(
        "pytest refuses DATABASE_URL/TEST_DATABASE_URL pointing at app DB 'orvia' "
        "(TRUNCATE would wipe registered users). Use orvia_test "
        f"(default: {_DEFAULT_TEST_DATABASE_URL}) or set TEST_ALLOW_APP_DB=1."
    )

os.environ["APP_ENV"] = "development"
# Force test DB even if shell/.env set DATABASE_URL to the app database.
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-use-only")
os.environ.setdefault(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
)
os.environ.setdefault("OUTBOX_WORKER_ENABLED", "false")
os.environ.setdefault("OUTBOX_RETRY_BASE_SECONDS", "0")
os.environ.setdefault("OUTBOX_PROCESSING_TIMEOUT_SECONDS", "300")
os.environ.setdefault("STORAGE_PROVIDER", "memory")
os.environ["AUTH_LOGIN_RATE_LIMIT_ENABLED"] = "true"
os.environ["AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS"] = "5"
os.environ["AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"
os.environ["AUTH_PASSWORD_MIN_LENGTH"] = "10"

from app.core.security import generate_invitation_token  # noqa: E402
from app.db.database import get_db  # noqa: E402
from app.db.seed import seed_roles  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
CAPTURED_INVITATION_TOKENS: list[str] = []


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return engine


@pytest.fixture(scope="session", autouse=True)
def _seed(engine) -> None:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_memory_storage() -> Generator[None, None, None]:
    from app.services.storage_provider import reset_memory_storage

    reset_memory_storage()
    yield
    reset_memory_storage()


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables(engine) -> Generator[None, None, None]:
    yield
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE notifications, outbox_events, notification_settings, pod_evidence, proof_of_deliveries, "
                "shipment_rider_assignments, shipment_status_history, "
                "shipments, riders, customers, organization_invitations, audit_logs, "
                "login_attempt_windows, platform_admin_grants, organization_memberships, organizations, "
                "users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(autouse=True)
def invitation_tokens(monkeypatch) -> list[str]:
    CAPTURED_INVITATION_TOKENS.clear()

    def _capture() -> str:
        token = generate_invitation_token()
        CAPTURED_INVITATION_TOKENS.append(token)
        return token

    monkeypatch.setattr("app.services.member_service.generate_invitation_token", _capture)
    return CAPTURED_INVITATION_TOKENS


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
