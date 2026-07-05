from pydantic import BaseModel, ConfigDict, Field, EmailStr


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=15)
    email: EmailStr = Field(max_length=50)
    
class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str