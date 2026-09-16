"""/api/auth 路由。"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import (
    RegisterRequest, LoginRequest, RefreshRequest,
    TokenResponse, UserOut,
)
from lumos.api.deps import get_db, get_current_user
from lumos.api.auth_utils import (
    hash_password, verify_password,
    create_token_pair, decode_token,
)
from lumos.persistence.repositories.users import UserRepository
from lumos.persistence.models import User, RevokedToken
from lumos.config import get_config
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(req.email):
        raise HTTPException(409, "email already registered")
    cfg = get_config()
    user = await repo.create(
        email=req.email, password_hash=hash_password(req.password, rounds=cfg.auth.bcrypt_rounds),
    )
    pair = create_token_pair(
        user.id, secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "user disabled")
    cfg = get_config()
    pair = create_token_pair(
        user.id, secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    cfg = get_config()
    try:
        payload = decode_token(req.refresh_token, secret=cfg.auth.jwt_secret, expected_type="refresh")
    except Exception:
        raise HTTPException(401, "invalid refresh token")
    # 检查撤销名单
    from sqlalchemy import select
    stmt = select(RevokedToken).where(RevokedToken.jti == req.refresh_token[:36])
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(401, "refresh token revoked")
    pair = create_token_pair(
        payload["sub"], secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=204)
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    cfg = get_config()
    try:
        payload = decode_token(req.refresh_token, secret=cfg.auth.jwt_secret, expected_type="refresh")
    except Exception:
        raise HTTPException(401, "invalid refresh token")
    expires_at = datetime.utcfromtimestamp(payload["exp"])
    revoked = RevokedToken(
        jti=req.refresh_token[:36], user_id=payload["sub"],
        expires_at=expires_at,
    )
    db.add(revoked)
    await db.commit()
    return None


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id, email=user.email,
        created_at=user.created_at, is_active=user.is_active,
    )