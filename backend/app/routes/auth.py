"""
Authentication endpoints.

Provides:
- Registration (email/password) with password length validation (min 8 chars)
- Login (sets httpOnly cookie AND returns token body for Swagger)
- Logout (clears cookie)
- Protected 'me' endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, field_validator

from app.db.session import get_db
from app.models.user import User
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


# ---------- Request/Response Schemas ----------
class UserCreate(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Ensure password is at least 8 characters long."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserResponse(BaseModel):
    """Response schema for user data (excludes password hash)."""

    id: str
    email: str
    created_at: str


class TokenResponse(BaseModel):
    """JWT token response (for Swagger/API clients)."""

    access_token: str
    token_type: str = "bearer"


class RegisterResponse(UserResponse, TokenResponse):
    """Response for registration - includes user data and JWT token."""

    pass  # Inherits all attributes. No need to declare manually.


# ---------- Endpoints ----------
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.

    - Checks if email already exists.
    - Validates password length (min 8 characters).
    - Hashes the password with Argon2.
    - Stores user in database.
    """
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, password_hash=hashed)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "ver": new_user.token_version})

    # Set httpOnly cookie (for React frontend)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production (HTTPS only)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return RegisterResponse(
        id=str(new_user.id),
        email=new_user.email,
        created_at=new_user.created_at.isoformat(),
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and set httpOnly cookie.

    - Validates email and password.
    - Creates JWT token.
    - Stores token in httpOnly cookie (for React).
    - Also returns token in JSON body (for Swagger UI / API clients).

    The cookie is automatically sent with subsequent requests.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "ver": user.token_version})

    # Set httpOnly cookie (for React frontend)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production (HTTPS only)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    # Return token in body (for Swagger / API clients)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout – bumps token_version to invalidate all existing tokens, then clears the cookie.
    """
    current_user.token_version += 1
    await db.commit()
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile.

    Protected endpoint – works with either:
    - httpOnly cookie (React)
    - Authorization Bearer header (Swagger)
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )
