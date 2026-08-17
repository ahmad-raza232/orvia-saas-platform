from sqlalchemy.orm import Session

from app.models.role import SEED_ROLES, Role


def seed_roles(db: Session) -> None:
    existing = {row.code for row in db.query(Role).all()}
    for code, name, scope in SEED_ROLES:
        if code not in existing:
            db.add(Role(code=code, name=name, scope=scope))
    db.commit()
