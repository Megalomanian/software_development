"""Auth endpoints — register, login, current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.core.dependencies import get_db
from backend.models_db.user import User

router = APIRouter()


@router.post("/register")
async def register(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        raise HTTPException(status_code=422, detail="username, email, password are required")
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    # Check uniqueness
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    existing = await db.scalar(select(User).where(User.username == username))
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.commit()

    # Return token so user is immediately logged in
    token = create_access_token({"sub": str(user.id)})
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(data: dict, db: AsyncSession = Depends(get_db)):
    """Login with email + password, return JWT token."""
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password are required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": str(current_user.created_at),
    }


@router.get("/users")
async def list_users(
    offset: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all users (requires authentication)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "created_at": str(u.created_at),
        }
        for u in users
    ]
