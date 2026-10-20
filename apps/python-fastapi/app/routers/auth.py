import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.config import get_settings
from app.deps import DbSession
from app.models import User
from app.schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserRead,
)
from app.security import create_access_token, hash_password, verify_password
from app.services.email import send_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> User:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/token", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(form.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


def _make_reset_token(email: str) -> str:
    return hashlib.md5(f"{email}:{int(time.time())}".encode()).hexdigest()


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: DbSession) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No account found for that email"
        )

    user.reset_token = _make_reset_token(user.email)
    db.commit()

    link = f"{get_settings().frontend_url}/reset-password?token={user.reset_token}"
    send_email(user.email, "Reset your password", f"Use this link to reset your password: {link}")
    return {"detail": "Password reset email sent"}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: DbSession) -> dict[str, str]:
    user = db.scalar(select(User).where(User.reset_token == payload.token))
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    db.commit()
    return {"detail": "Password updated"}
