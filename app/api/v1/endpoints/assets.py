from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.api.core.database import get_async_db
from app.api.models.user import User
from app.api.models.asset import Asset, AssetStatus
from app.api.models.category import Category
from app.api.models.location import Location
from app.api.schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetWithRelationsResponse
from app import deps

router = APIRouter()

@router.get("/", response_model=List[AssetResponse])
async def get_assets(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    category_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    status: Optional[AssetStatus] = Query(None),
    search: Optional[str] = Query(None, description="Поиск по названию, инвентарному или серийному номеру"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Получение списка имущества с фильтрацией.
    Администраторы видят всё, обычные пользователи - только закрепленное за ними или их отдела.
    """
    query = select(Asset)
    
    # Если пользователь не админ, показываем только его имущество
    if not current_user.is_admin:
        query = query.where(
            or_(
                Asset.assignee_id == current_user.id,
                Asset.registered_by_id == current_user.id
            )
        )
    
    # Применяем фильтры
    if category_id:
        query = query.where(Asset.category_id == category_id)
    if location_id:
        query = query.where(Asset.location_id == location_id)
    if assignee_id and current_user.is_admin:
        query = query.where(Asset.assignee_id == assignee_id)
    if status:
        query = query.where(Asset.status == status)
    
    # Поиск по тексту
    if search:
        query = query.where(
            or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.inventory_number.ilike(f"%{search}%"),
                Asset.serial_number.ilike(f"%{search}%"),
                Asset.barcode.ilike(f"%{search}%")
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(Asset.created_at.desc())
    
    result = await db.execute(query)
    assets = result.scalars().all()
    return assets


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_in: AssetCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Создание новой записи об имуществе"""
    
    # Проверяем уникальность инвентарного номера
    result = await db.execute(
        select(Asset).where(Asset.inventory_number == asset_in.inventory_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory number already exists"
        )
    
    # Проверяем существование категории, если указана
    if asset_in.category_id:
        result = await db.execute(
            select(Category).where(Category.id == asset_in.category_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    
    # Проверяем существование локации, если указана
    if asset_in.location_id:
        result = await db.execute(
            select(Location).where(Location.id == asset_in.location_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
    
    # Проверяем существование ответственного, если указан
    if asset_in.assignee_id:
        result = await db.execute(
            select(User).where(User.id == asset_in.assignee_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignee not found"
            )
    
    # Создаем имущество
    asset = Asset(
        **asset_in.model_dump(),
        registered_by_id=current_user.id,
        current_value=asset_in.purchase_cost
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return asset

@router.get("/{asset_id}", response_model=AssetWithRelationsResponse)
async def get_asset(
    asset_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Получение детальной информации об имуществе"""
    
    query = select(Asset).where(Asset.id == asset_id)

    query = query.options(
        selectinload(Asset.category),
        selectinload(Asset.location),
        selectinload(Asset.assignee),
        selectinload(Asset.registrar)
    )
    
    result = await db.execute(query)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Проверяем права доступа
    if not current_user.is_admin and \
       asset.assignee_id != current_user.id and \
       asset.registered_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Формируем ответ с дополнительными полями
    response = AssetWithRelationsResponse.model_validate(asset)
    response.category_name = asset.category.name if asset.category else None
    response.location_name = asset.location.name if asset.location else None
    response.assignee_name = asset.assignee.full_name if asset.assignee else None
    response.registrar_name = asset.registrar.full_name
    
    return response


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Обновление информации об имуществе"""

    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Проверяем права (только администратор или регистратор может изменять)
    if not current_user.is_admin and asset.registered_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Обновляем поля
    update_data = asset_in.model_dump(exclude_unset=True)
    
    # Проверяем связанные записи при изменении
    if "category_id" in update_data and update_data["category_id"]:
        result = await db.execute(
            select(Category).where(Category.id == update_data["category_id"])
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    
    if "location_id" in update_data and update_data["location_id"]:
        result = await db.execute(
            select(Location).where(Location.id == update_data["location_id"])
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
    
    if "assignee_id" in update_data and update_data["assignee_id"]:
        result = await db.execute(
            select(User).where(User.id == update_data["assignee_id"])
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignee not found"
            )
    
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    await db.commit()
    await db.refresh(asset)
    
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Удаление записи об имуществе.
    Только для администраторов или если имущество не использовалось.
    """
    
    # Получаем имущество
    result = await db.execute(
        select(Asset)
        .where(Asset.id == asset_id)
        .options(selectinload(Asset.movements))
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Проверяем права
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete assets"
        )
    
    if asset.movements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete asset with movement history. Consider decommissioning instead."
        )
    
    await db.delete(asset)
    await db.commit()