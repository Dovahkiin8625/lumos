"""FastAPI依赖注入。"""
from __future__ import annotations
from typing import AsyncIterator
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.db import get_session_factory
from lumos.persistence.models import User
from lumos.persistence.repositories.users import UserRepository
from lumos.api.auth_utils import decode_token


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = get_session_factory(request.app.state.engine)
    async with factory() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    secret = __import__("lumos.api.deps_helper", fromlist=["get_jwt_secret"]).get_jwt_secret()
    try:
        payload = decode_token(token, secret=secret, expected_type="access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    repo = UserRepository(db)
    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found",
        )
    return user
