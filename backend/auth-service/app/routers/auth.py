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
