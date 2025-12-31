from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select

from app.schemas.user import (
    UserRegisterSchema, 
    UserLoginSchema, 
    UserPublicSchema, 
    RefreshTokenSchema
)

from app.models.user import User
from app.database import async_session
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token
from app.core.dependencies import get_current_user
from app.core.refresh import create_refresh_token_session, validate_refresh_token

import sqlalchemy as sa
from app.models.user_sessions import UserSession

from datetime import datetime, timezone


router = APIRouter()


@router.post("/register", status_code=201)
async def register_user(payload: UserRegisterSchema):
    """
    Register a new user.
    """
    async with async_session() as session:

        # 1) Check email duplication
        result_email = await session.execute(
            select(User).where(User.email == payload.email)
        )
        if result_email.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # 2) Check alias duplication (if provided)
        if payload.alias:
            result_alias = await session.execute(
                select(User).where(User.alias == payload.alias)
            )
            if result_alias.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Alias already in use"
                )

        # 3) Hash password
        hashed_pw = hash_password(payload.password)

        # 4) Create new user
        new_user = User(
            email=payload.email,
            alias=payload.alias,              # now nullable: OK
            password_hash=hashed_pw,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        # 5) Response (never include password)
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "alias": new_user.alias,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "created_at": new_user.created_at,
        }


@router.post("/login")
async def login_user(payload: UserLoginSchema):
    """
    Authenticate user and return a JWT access token.
    """
    async with async_session() as session:
        # 1) Find user by email
        result = await session.execute(
            select(User).where(User.email == payload.email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Do not reveal whether the email exists for security reasons
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 🚫 NEW: block logins for soft-deleted users
        if user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been deleted",
            )

        # 2) Verify password
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        
        # 3) Create the short-lived access token (JWT)
        access_token = create_access_token(
            data={"sub": str(user.id)}
)
        
        # 4) Create a long-lived refresh token session
        refresh_token = await create_refresh_token_session(
            user_id=str(user.id),
            user_agent=None,     # deferred for Security Hardening Pass
            ip_address=None      # deferred as well
        )

        
        # Update last_login_at
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)
        await session.commit()
        await session.refresh(user)


        # 5) Return both tokens to the client
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
}


# Endpoint protegido: requiere JWT
@router.get("/me", response_model=UserPublicSchema)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Return the authenticated user's public profile.

    FastAPI will automatically convert the SQLAlchemy User object
    into the Pydantic UserPublicSchema thanks to orm_mode = True.
    """
    return current_user


@router.post("/refresh-token")
async def refresh_access_token(payload: RefreshTokenSchema):
    """
    Exchange a valid refresh token for a new access token.
    This endpoint:
    - validates the refresh token
    - loads the user session
    - issues a new access token
    """
    
    # 1. Validate refresh token and load session
    stored_session = await validate_refresh_token(
        refresh_token=payload.refresh_token
    )
    
    # 2. Create new access token (same user)
    new_access_token = create_access_token(
        data={"sub": str(stored_session.user_id)}
    )
    
    # 3. Return only the new access token (no rotation yet)
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout_user(payload: RefreshTokenSchema):
    """
    Logs out the user by invalidating the refresh token session.
    
    Steps:
    - Validate refresh token
    - Delete the corresponding session
    - Confirm logout
    """
    
    async with async_session() as session:
        
        # 1) Validate the refresh token (loads the UserSession)
        stored_session = await validate_refresh_token(
            refresh_token=payload.refresh_token
        )
        
        # 2) Delete the session from the database
        await session.delete(stored_session)
        await session.commit()
        
        # 3) Confirm logout
        return {"detail": "User logged out successfully"}


@router.post("/logout-all")
async def logout_user_from_all_devices(
    current_user: User = Depends(get_current_user)
):
    """
    Logs out the user from ALL devices by deleting all refresh token
    sessions associated with the authenticated user.
    
    This is useful when:
    - a device is lost
    - suspicious activity is detected
    - the user wants a global session reset
    """
    
    async with async_session() as session:
        
        # 1. Delete all sessions for this user
        await session.execute(
            sa.delete(UserSession).where(
                UserSession.user_id == current_user.id
            )
        )
        
        # 2. Commit changes
        await session.commit()
        
        # 3. Response
        return {"detail": "Logged out from all devices successfully"}


@router.get("/sessions")
async def list_active_sessions(current_user: User = Depends(get_current_user)):
    """
    Return all active refresh-token sessions for the authenticated user.
    
    This helps users (and administrators) see:
    - which devices are logged in
    - when each session was created
    - when each session expires
    
    In the future:
    - user_agent and ip_address will be filled (Security Hardening Pass)
    """
    async with async_session() as session:
        
        # 1) Query all sessions belonging to the current user
        result = await session.execute(
            select(UserSession).where(UserSession.user_id == current_user.id)
        )
        
        sessions = result.scalars().all()
        
        # 2) Convert sessions to JSON-serializable form
        serialized = [
            {
                "id": str(s.id),
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "user_agent": s.user_agent,
                "ip_address": s.ip_address,
            }
            for s in sessions
        ]
        
        return {"sessions": serialized}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific refresh-token session belonging to the authenticated user.
    
    This endpoint:
    - ensures the session exists
    - ensures it belongs to the requesting user
    - deletes only that session
    
    This mirrors session-management features found in professional applications.
    """
    
    async with async_session() as session:
        
        # 1) Query the session from DB
        result = await session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        stored_session = result.scalar_one_or_none()
        
        # 2) If session doesn't exist → error
        if stored_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # 3) Prevent deleting sessions from other users
        if stored_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to delete this session"
            )
        
        # 4) Delete the session
        await session.delete(stored_session)
        await session.commit()
        
        # 5) Response
        return {"detail": "Session deleted successfully"}

@router.delete("/delete-account")
async def delete_account(current_user: User = Depends(get_current_user)):
    """
    Soft-delete the authenticated user's account.
    
    - Removes personal data (GDPR compliant)
    - Marks user as deleted
    - Invalidates all sessions
    """
    async with async_session() as session:
        
        # 1. Load the full user instance
        user = current_user
        
        # 2. GDPR compliance -> UPDATE: these can't be nullified.
        # user.email = None
        # user.alias = None
        # user.first_name = None
        # user.last_name = None
        
        # 3. Mark user as deleted
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        
        session.add(user)
        
        # 4. Invalidate all sessions
        await session.execute(
            sa.delete(UserSession).where(UserSession.user_id == user.id)
        )
        
        # 5. Commit changes
        await session.commit()
        
        return {"detail": "Account deleted successfully"}
