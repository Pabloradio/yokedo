from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class UserRegisterSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    alias: str | None = Field(default=None, max_length=50)

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserPublicSchema(BaseModel):
    """
    Esquema público del usuario.
    Este modelo se usa para respuestas hacia el frontend.
    No incluye datos sensibles como password_hash.
    """
    id: UUID = Field(..., description="User ID as UUID string")
    email: EmailStr
    alias: str | None = None
    first_name: str
    last_name: str
    created_at: datetime

    class Config:
        # Permite que Pydantic convierta automáticamente objetos SQLAlchemy
        orm_mode = True