from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.core.database import get_db
from app.api.core import security
from app.api.core.config import settings
from app.api.models.user import User
from app.api.schemas.auth import Token, LoginRequest, ChangePasswordRequest
from app.api.schemas.user import UserCreate, UserResponse
from app import deps

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request
):
    """
    Регистрация нового пользователя
    """

    # Проверяем, не занят ли email
    result = db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Проверяем, не занят ли username
    result = db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Создаем пользователя
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        department=user_in.department,
        position=user_in.position,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
        is_admin=False  # Обычные пользователи не админы
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    

    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response
):
    """
    Вход в систему
    """
    # Ищем пользователя по email или username
    result = db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    # Проверяем пароль
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем, активен ли пользователь
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user. Please contact administrator."
        )
    
    # Создаем токены
    access_token = security.create_access_token(
        {"sub": str(user.id), "username": user.username, "is_admin": user.is_admin}
    )
    refresh_token = security.create_access_token(
        {"sub": str(user.id)}
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response
):
    """
    Вход в систему (JSON версия)
    """
    # Ищем пользователя по email или username
    result = db.execute(
        select(User).where(
            (User.email == login_data.username) | (User.username == login_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = security.create_access_token(
        {"sub": str(user.id), "username": user.username, "is_admin": user.is_admin}
    )
    refresh_token = security.create_access_token(
        {"sub": str(user.id)}
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    response: Response
):
    """
    Выход из системы
    Удаляет refresh token из cookie
    """
    response.delete_cookie(key="refresh_token")
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Получение информации о текущем авторизованном пользователе.
    """
    return current_user


@router.post("/change-password")
async def change_password(
    passwords: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Смена пароля текущим пользователем.
    Требуется указать старый пароль для подтверждения.
    """

    # Проверяем старый пароль
    if not security.verify_password(passwords.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    # Проверяем, что новый пароль отличается от старого
    if security.verify_password(passwords.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password"
        )
    
    # Устанавливаем новый пароль
    current_user.hashed_password = security.get_password_hash(passwords.new_password)
    db.add(current_user)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/check-token")
async def check_token(
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Проверка валидности токена.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin
    }
