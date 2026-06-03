from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        """Repository for auth user persistence."""
        self.session = session

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Fetch a user by primary key."""
        return self.session.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email address."""
        return self.session.query(User).filter(User.email == email).first()

    def get_by_oauth(self, provider: str, oauth_id: str) -> Optional[User]:
        """Fetch a user by OAuth provider and provider-specific ID."""
        return (
            self.session.query(User)
            .filter(User.oauth_provider == provider, User.oauth_id == oauth_id)
            .first()
        )

    def list_by_institution(self, institution_id: int):
        """List all users in the given institution."""
        return (
            self.session.query(User).filter(User.institution_id == institution_id).all()
        )

    def list_all(self):
        """List all users across all institutions (Super Admin)."""
        return self.session.query(User).all()

    def assign_role(self, user: User, role: str) -> User:
        """Assign a new role to an existing user."""
        user.role = role
        self.session.commit()
        self.session.refresh(user)
        return user

    def upsert_oauth_user(
        self,
        email: str,
        provider: str,
        oauth_id: str,
        full_name: Optional[str],
        institution_id: int,
        default_role: str = "end_user",
    ) -> Tuple[User, bool]:
        """Create or update a user based on OAuth identity and email."""
        user = self.get_by_oauth(provider, oauth_id)
        created = False
        if not user and email:
            user = self.get_by_email(email)
        if user:
            if user.oauth_provider != provider or user.oauth_id != oauth_id:
                user.oauth_provider = provider
                user.oauth_id = oauth_id
            user.last_login = datetime.utcnow()
            self.session.commit()
            self.session.refresh(user)
            return user, created

        user = User(
            email=email,
            full_name=full_name,
            role=default_role,
            institution_id=institution_id,
            oauth_provider=provider,
            oauth_id=oauth_id,
            last_login=datetime.utcnow(),
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        created = True
        return user, created
