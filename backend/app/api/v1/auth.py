
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    issue_token,
    current_user,
)
from app.models import User
from app.schemas.auth import (
    Register,
    Login,
    Token,
    UserProfile,
)

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=Token, status_code=201)
def register(payload: Register, db: Session = Depends(get_db)):
    email = str(payload.email).lower()

    if db.get_bind().dialect.name == "postgresql":

        user_id = db.scalar(
            text(
                "SELECT sentinel_security.register_officer("
                ":uid, :email, :password_hash)"
            ),
            {
                "uid": str(uuid4()),
                "email": email,
                "password_hash": hash_password(payload.password),
            },
        )

        if user_id is None:
            db.rollback()
            raise HTTPException(409, "Email already registered")

        db.commit()

        return Token(
            access_token=issue_token(User(id=user_id))
        )


    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role='officer',
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return Token(access_token=issue_token(user))


@router.post('/login', response_model=Token)
def login(payload: Login, db: Session = Depends(get_db)):

    if db.get_bind().dialect.name == "postgresql":

        record = db.execute(
            text(
                "SELECT * FROM sentinel_security.login_lookup("
                ":email)"
            ),
            {"email": str(payload.email).lower()},
        ).one_or_none()

        if (
            record is None
            or not record.active
            or not verify_password(
                payload.password, record.password_hash
            )
        ):
            raise HTTPException(401, "Invalid credentials")

        return Token(
            access_token=issue_token(User(id=record.id))
        )

    user = db.scalar(
        select(User).where(
            User.email == str(payload.email).lower()
        )
    )

    if (
        user is None
        or not user.active
        or not verify_password(
            payload.password,
            user.password_hash
        )
    ):
        raise HTTPException(401, 'Invalid credentials')

    return Token(access_token=issue_token(user))


@router.get('/me', response_model=UserProfile)
def get_me(user: User = Depends(current_user)):
    return UserProfile(
        id=user.id,
        email=user.email,
        role=user.role,
        active=user.active,
    )
