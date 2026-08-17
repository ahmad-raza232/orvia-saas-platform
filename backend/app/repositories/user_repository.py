from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import normalize_email


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == normalize_email(email)).one_or_none()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
