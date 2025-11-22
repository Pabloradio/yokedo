from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.schemas.user import UserRegisterSchema, UserLoginSchema, UserPublicSchema
from app.models.user import User
from app.database import async_session
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token

from fastapi import Depends
from app.core.dependencies import get_current_user


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

        # 3) Create JWT token (subject = user id)
        access_token = create_access_token(
            data={"sub": str(user.id)}
        )

        # 4) Optionally, you could update last_login_at here
        #    when you add that field to the SQLAlchemy model.

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
    

# Endpoint protegido: requiere JWT
@router.get("/me", response_model=UserPublicSchema)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Devuelve el perfil del usuario autenticado usando un esquema Pydantic.
    
    - Esta función no hace nada complicada.
    - Toda la lógica de autenticación se realiza en get_current_user().
    - Si el token es válido, current_user será un objeto User real.
    - Si el token no es válido, FastAPI devolverá 401 automáticamente.

    Este endpoint sirve para verificar fácilmente 
    que la autenticación por JWT funciona correctamente.
    """
    
    # Aquí simplemente seleccionamos qué datos queremos devolver.
    # Nunca incluimos datos sensibles como password_hash.
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "alias": current_user.alias,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "created_at": current_user.created_at,
    }

