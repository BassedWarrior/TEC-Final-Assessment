"""
FastAPI dependencies.

Provides 'get_current_user' to extract and validate JWT from:
1. Authorization header (Bearer token) – for Swagger UI / external clients.
2. httpOnly cookie – for the React frontend.

This dual approach keeps Swagger usable while maintaining secure cookie auth.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.config import settings

# OAuth2 scheme for Swagger (auto_error=False allows fallback to cookie)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Retrieve the current authenticated user.

    Authentication order:
    1. Authorization header (Bearer token) – used by Swagger UI.
    2. httpOnly cookie named 'access_token' – used by React frontend.

    Raises 401 if no token found or token is invalid.
    """
    # Try header first (Swagger)
    access_token = token

    # Fallback to cookie (React)
    if not access_token:
        access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_ver: int = payload.get("ver")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if token_ver is None or token_ver != user.token_version:
        raise credentials_exception
    return user
