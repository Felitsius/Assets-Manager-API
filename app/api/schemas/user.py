from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=72)
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=72) 
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        if v and len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=72) 
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserListResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: EmailStr
    is_active: bool
    is_admin: bool
    
    model_config = ConfigDict(from_attributes=True)