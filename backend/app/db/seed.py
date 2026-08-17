import logging

from sqlalchemy.orm import Session

from app.models.role import SEED_ROLES, Role
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.organization import OrganizationCreate
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService

logger = logging.getLogger("orvia.seed")


def seed_roles(db: Session) -> None:
    existing = {row.code for row in db.query(Role).all()}
    for code, name, scope in SEED_ROLES:
        if code not in existing:
            db.add(Role(code=code, name=name, scope=scope))
    db.commit()


def seed_demo_workspace(
    db: Session,
    *,
    email: str,
    password: str,
    org_name: str = "ORVIA Demo",
) -> None:
    """
    Create a durable demo tenant if it does not already exist.
    Never overwrites an existing user, password, or organization.
    """
    seed_roles(db)
    cleaned_email = (email or "").strip().lower()
    if not cleaned_email or not (password or "").strip():
        logger.warning("demo seed skipped: DEMO_SEED_EMAIL and DEMO_SEED_PASSWORD are required")
        return

    existing = db.query(User).filter(User.email == cleaned_email).one_or_none()
    if existing is not None:
        logger.info("demo seed skipped: account already exists for %s", cleaned_email)
        return

    first, _, rest = cleaned_email.partition("@")
    user = AuthService(db).register(
        RegisterRequest(
            email=cleaned_email,
            password=password,
            first_name=(first or "Demo").replace(".", " ").title()[:80] or "Demo",
            last_name="Operator",
            phone=None,
        )
    )
    OrganizationService(db).create_for_user(
        user,
        OrganizationCreate(name=org_name.strip() or "ORVIA Demo", slug="orvia-demo"),
    )
    logger.info("demo workspace created for %s", cleaned_email)
