from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.core.database import get_async_db
from app.api.models.user import User
from app.api.models.asset import Asset
from app.api.models.location import Location
from app.api.models.movement import Movement, MovementType
from app.api.schemas.movement import MovementCreate, MovementResponse
from app import deps

router = APIRouter()

@router.get("/asset/{asset_id}", response_model=List[MovementResponse])
async def get_asset_movements(
    asset_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Получение истории перемещений конкретного имущества"""
    
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    if not current_user.is_admin and \
       asset.assignee_id != current_user.id and \
       asset.registered_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    result = await db.execute(
        select(Movement)
        .where(Movement.asset_id == asset_id)
        .order_by(Movement.movement_date.desc())
        .offset(skip)
        .limit(limit)
    )
    
    movements = result.scalars().all()
    return movements


@router.post("/", response_model=MovementResponse, status_code=status.HTTP_201_CREATED)
async def create_movement(
    movement_in: MovementCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Создание записи о перемещении имущества
    """
    
    result = await db.execute(
        select(Asset).where(Asset.id == movement_in.asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    if not current_user.is_admin and asset.assignee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assignee or admin can move this asset"
        )
    
    if movement_in.movement_type == MovementType.ASSIGN:
        if not movement_in.to_assignee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee required for ASSIGN movement"
            )
        
        result = await db.execute(
            select(User).where(User.id == movement_in.to_assignee_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignee not found"
            )
        
        asset.assignee_id = movement_in.to_assignee_id
        
    elif movement_in.movement_type == MovementType.TRANSFER:
        if not movement_in.to_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target location required for TRANSFER movement"
            )

        result = await db.execute(
            select(Location).where(Location.id == movement_in.to_location_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target location not found"
            )
        
        asset.location_id = movement_in.to_location_id
    
    elif movement_in.movement_type == MovementType.RETURN:
        asset.assignee_id = None
    
    movement = Movement(
        **movement_in.model_dump(),
        initiated_by_id=current_user.id
    )
    
    db.add(movement)
    db.add(asset)
    await db.commit()
    await db.refresh(movement)
    
    return movement