# app/core/dependencies.py

# Importamos herramientas de FastAPI para declarar dependencias
from fastapi import Depends, HTTPException, status

# Importamos SQLAlchemy para hacer consultas
from sqlalchemy import select

# Importamos la sesión asíncrona que usamos en todo el microservicio
from app.database import async_session

# Importamos el modelo User, porque lo necesitaremos para cargar el usuario desde la BD
from app.models.user import User

# Importamos la función que decodifica tokens JWT
from app.core.jwt import decode_access_token

# Importamos la clase que nos permite extraer el token "Bearer" automáticamente
from fastapi.security import HTTPBearer


# Creamos un esquema simple de autenticación Bearer
bearer_scheme = HTTPBearer()


# -----------------------------
# 2) FUNCIÓN PRINCIPAL:
#    get_current_user()
# -----------------------------
async def get_current_user(credentials = Depends(bearer_scheme)):
    """
    Devuelve el usuario autenticado a partir del token JWT.

    Esta función será llamada automáticamente por FastAPI
    cuando un endpoint declare:
        current_user: User = Depends(get_current_user)

    Pasos:
    1. Recibe el token desde la cabecera Authorization.
    2. Decodifica el token.
    3. Extrae el user_id del payload ("sub").
    4. Busca al usuario en la base de datos.
    5. Lo devuelve al endpoint.
    """
    token = credentials.credentials  # El token puro, sin "Bearer " delante

    # -----------------------------
    # (A) Verificar que tenemos un token
    # -----------------------------
    if not token:
        # Si no hay token, devolvemos un error estándar '401 Unauthorized'
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------
    # (B) Intentar decodificar el token
    # -----------------------------
    try:
        payload = decode_access_token(token)
        # Esperamos que el token tenga un campo "sub"
        # que contiene el ID del usuario.
        user_id = payload.get("sub")

        if user_id is None:
            # Esto sería un token inválido
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception:
        # Cualquier excepción en la decodificación (expirado, mal formado, firmado con clave incorrecta…)
        # nos obliga a devolver un error 401 estándar
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------
    # (C) Look up the user in the database
    # -----------------------------
    async with async_session() as session:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            # User not found in DB
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user account is active
        if not user.is_active:
            # Deny access if account is disabled
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user account was soft-deleted
        if user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been deleted",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Everything OK: return the authenticated user
        return user
