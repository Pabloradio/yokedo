from pydantic import BaseModel, EmailStr, Field

class UserRegisterSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    alias: str | None = Field(default=None, max_length=50)
