from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import (
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from services.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_user_by_email,
    hash_password,
    revoke_all_user_tokens,
    revoke_refresh_token,
    verify_refresh_token,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if data.role not in {"landowner", "company"}:
        raise HTTPException(status_code=400, detail="Role must be landowner or company")
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=data.role,
        full_name=data.full_name,
        organization=data.organization,
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login_json(data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email.lower(), data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(user.id, user.role, user.email)
    raw_refresh, _ = create_refresh_token(db, user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        full_name=user.full_name,
        user_id=user.id,
    )


@router.post("/token", response_model=TokenResponse)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username.lower(), form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(user.id, user.role, user.email)
    raw_refresh, _ = create_refresh_token(db, user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        full_name=user.full_name,
        user_id=user.id,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    user = verify_refresh_token(db, body.refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old refresh token (rotation)
    revoke_refresh_token(db, body.refresh_token)

    # Issue new tokens
    access_token = create_access_token(user.id, user.role, user.email)
    raw_refresh, _ = create_refresh_token(db, user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        full_name=user.full_name,
        user_id=user.id,
    )


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    """Revoke the given refresh token."""
    revoked = revoke_refresh_token(db, body.refresh_token)
    return {"message": "Logged out" if revoked else "Token not found or already revoked"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
