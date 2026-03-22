from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.core.database import get_async_db
from app.api.models.user import User
from app.api.models.location import Location
from app.api.models.asset import Asset
from app.api.schemas.location import (
    LocationCreate, LocationUpdate, LocationResponse,
    LocationWithChildrenResponse, LocationWithStatsResponse
)
from app import deps

router = APIRouter()

@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    building: Optional[str] = Query(None)
):
    """Получение списка местоположений"""
    
    query = select(Location)
    
    if building:
        query = query.where(Location.building == building)
    
    query = query.offset(skip).limit(limit).order_by(Location.name)
    
    result = await db.execute(query)
    locations = result.scalars().all()
    return locations


@router.get("/tree", response_model=List[LocationWithChildrenResponse])
async def get_location_tree(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Получение иерархического дерева местоположений"""
    
    result = await db.execute(select(Location))
    locations = result.scalars().all()
    
    # Строим дерево
    location_dict = {loc.id: LocationWithChildrenResponse.model_validate(loc) for loc in locations}
    roots = []
    
    for loc_id, loc in location_dict.items():
        if loc.parent_id:
            if loc.parent_id in location_dict:
                if not hasattr(location_dict[loc.parent_id], 'children'):
                    location_dict[loc.parent_id].children = []
                location_dict[loc.parent_id].children.append(loc)
        else:
            roots.append(loc)
    
    return roots




@router.get("/with-stats", response_model=List[LocationWithStatsResponse])
async def get_locations_with_stats(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]  # Только для админов
):
    """Получение местоположений со статистикой по имуществу"""
    
    result = await db.execute(
        select(
            Location,
            func.count(Asset.id).label('assets_count'),
            func.sum(Asset.purchase_cost).label('total_value')
        )
        .outerjoin(Asset, Asset.location_id == Location.id)
        .group_by(Location.id)
        .order_by(Location.name)
    )
    
    locations_with_stats = []
    for location, assets_count, total_value in result.all():
        loc_response = LocationWithStatsResponse.model_validate(location)
        loc_response.assets_count = assets_count
        loc_response.total_value = float(total_value) if total_value else 0
        locations_with_stats.append(loc_response)
    
    return locations_with_stats


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_in: LocationCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]
):
    """Создание нового местоположения"""

    stmt = select(Location).where(Location.name == location_in.name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
        
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name already exists"
        )
        
    if location_in.parent_id:
        stmt_parent = select(Location).where(Location.id == location_in.parent_id)
        result_parent = await db.execute(stmt_parent)
        parent = result_parent.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent location not found"
            )
        
    location = Location(**location_in.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    return location


@router.get("/{location_id}", response_model=LocationWithChildrenResponse)
async def get_location(
    location_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Получение местоположения по ID с дочерними локациями"""
    
    result = await db.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.sublocations))
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    return location


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_in: LocationUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]
):
    """Обновление местоположения"""
    
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    if location_in.name and location_in.name != location.name:
        result = await db.execute(
            select(Location).where(Location.name == location_in.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location with this name already exists"
            )
    
    if location_in.parent_id == location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location cannot be parent of itself"
        )
    
    if location_in.parent_id:
        result = await db.execute(
            select(Location).where(Location.id == location_in.parent_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent location not found"
            )
    
    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]
):
    """
    Удаление местоположения.
    Нельзя удалить локацию, у которой есть имущество или дочерние локации.
    """
    
    result = await db.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.sublocations))
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    if location.sublocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete location with sublocations"
        )
    
    result = await db.execute(
        select(Asset).where(Asset.location_id == location_id).limit(1)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete location with assets"
        )
    
    await db.delete(location)
    await db.commit()


@router.get("/{location_id}/assets")
async def get_location_assets(
    location_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """Получение списка имущества в конкретном местоположении"""
    
    result = await db.execute(select(Location).where(Location.id == location_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    result = await db.execute(
        select(Asset)
        .where(Asset.location_id == location_id)
        .order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    
    return assets