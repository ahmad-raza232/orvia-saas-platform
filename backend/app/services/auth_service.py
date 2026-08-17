from app.core.exceptions import DuplicateEmailError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.services.organization_service import OrganizationService
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

__all__ = ["AuthService", "OrganizationService"]


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.memberships = MembershipRepository(db)

    def register(self, payload: RegisterRequest) -> User:
        if self.users.get_by_email(payload.email):
            raise DuplicateEmailError()
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
        )
        self.users.create(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateEmailError() from exc
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        from app.core.security import verify_password

        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
