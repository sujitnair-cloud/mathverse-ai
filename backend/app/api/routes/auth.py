"""
Google OAuth + JWT authentication routes.
POST /api/v1/auth/google  — exchange Google ID token for our JWT
GET  /api/v1/auth/me      — return current user info
POST /api/v1/auth/logout  — client-side only (just returns success)
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


class GoogleTokenRequest(BaseModel):
    credential: str  # Google ID token (JWT from Google One Tap / Sign-In button)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/google", response_model=AuthResponse)
async def google_auth(body: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured on this server")

    # Verify the Google ID token
    try:
        info = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_id = info["sub"]
    email = info.get("email", "")
    name = info.get("name", "")
    avatar = info.get("picture", "")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(google_id=google_id, email=email, name=name, avatar_url=avatar)
        db.add(user)
        await db.flush()
    else:
        user.name = name
        user.avatar_url = avatar
        user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    if current_user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
    }


@router.post("/logout")
async def logout():
    return {"message": "Logged out — delete the token from your browser."}
