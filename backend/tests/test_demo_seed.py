from sqlalchemy.orm import Session

from app.db.seed import seed_demo_workspace
from app.models.organization import Organization
from app.models.user import User


def test_demo_seed_creates_once_and_never_overwrites(db: Session) -> None:
    seed_demo_workspace(
        db,
        email="demo@orvia.app",
        password="DemoPass1234",
        org_name="ORVIA Demo",
    )
    user = db.query(User).filter(User.email == "demo@orvia.app").one()
    org = db.query(Organization).filter(Organization.slug == "orvia-demo").one()
    first_hash = user.password_hash
    first_org_id = org.id

    seed_demo_workspace(
        db,
        email="demo@orvia.app",
        password="DifferentPass123",
        org_name="Should Not Replace",
    )
    db.refresh(user)
    db.refresh(org)
    assert user.password_hash == first_hash
    assert org.id == first_org_id
    assert org.name == "ORVIA Demo"
    assert db.query(User).filter(User.email == "demo@orvia.app").count() == 1
    assert db.query(Organization).filter(Organization.slug == "orvia-demo").count() == 1


def test_demo_seed_skips_without_credentials(db: Session) -> None:
    seed_demo_workspace(db, email="", password="DemoPass1234")
    seed_demo_workspace(db, email="skipped@orvia.app", password="   ")
    assert db.query(User).count() == 0
    assert db.query(Organization).count() == 0
