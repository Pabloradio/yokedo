from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.schemas.user import UserRegisterSchema
from app.models.user import User
from app.database import async_session
from app.core.security import hash_password

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
