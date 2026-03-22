from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.api.core.database import get_async_db
from app.api.models.user import User
from app.api.models.category import Category
from app.api.models.asset import Asset
from app.api.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    CategoryWithChildrenResponse, CategoryWithStatsResponse,
    CategoryTreeResponse
)
from app import deps

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(100, ge=1, le=1000, description="Сколько вернуть"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    parent_id: Optional[int] = Query(None, description="Фильтр по родительской категории"),
    has_assets: Optional[bool] = Query(None, description="Только категории с имуществом")
):
    """
    Получение списка всех категорий.
    Доступно всем авторизованным пользователям.
    Поддерживает поиск и фильтрацию.
    """

    query = select(Category)
    
    if search:
        query = query.where(Category.name.ilike(f"%{search}%"))
    
    if parent_id is not None:
        if parent_id == 0:
            query = query.where(Category.parent_id.is_(None))
        else:
            query = query.where(Category.parent_id == parent_id)
    
    if has_assets is not None:
        if has_assets:
            query = query.where(
                select(func.count(Asset.id))
                .where(Asset.category_id == Category.id)
                .scalar_subquery() > 0
            )
        else:
            query = query.where(
                select(func.count(Asset.id))
                .where(Asset.category_id == Category.id)
                .scalar_subquery() == 0
            )
    
    query = query.offset(skip).limit(limit).order_by(Category.name)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return categories


@router.get("/tree", response_model=List[CategoryTreeResponse])
async def get_category_tree(
    db: Annotated[AsyncSession, Depends(get_async_db)]
):
    """
    Получение иерархического дерева категорий.
    """

    result = await db.execute(select(Category))
    categories = result.scalars().all()
    
    category_dict = {}
    for cat in categories:
        category_dict[cat.id] = CategoryTreeResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            parent_id=cat.parent_id,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            children=[]
        )
    
    roots = []
    for cat_id, cat in category_dict.items():
        if cat.parent_id and cat.parent_id in category_dict:
            category_dict[cat.parent_id].children.append(cat)
        else:
            roots.append(cat)
    
    return roots


@router.get("/flat", response_model=List[CategoryResponse])
async def get_categories_flat(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Получение плоского списка категорий.
    Возвращает все категории в виде простого списка.
    """

    result = await db.execute(
        select(Category).order_by(Category.name)
    )
    categories = result.scalars().all()
    return categories


@router.get("/with-stats", response_model=List[CategoryWithStatsResponse])
async def get_categories_with_stats(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)] 
):
    """
    Получение категорий со статистикой по имуществу.
    
    Возвращает для каждой категории:
    - Количество единиц имущества
    - Общая стоимость имущества
    - Средняя стоимость единицы
    """

    result = await db.execute(
        select(
            Category,
            func.count(Asset.id).label('assets_count'),
            func.sum(Asset.purchase_cost).label('total_value'),
            func.avg(Asset.purchase_cost).label('avg_value')
        )
        .outerjoin(Asset, Asset.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    
    categories_with_stats = []
    for category, assets_count, total_value, avg_value in result.all():
        cat_response = CategoryWithStatsResponse.model_validate(category)
        cat_response.assets_count = assets_count or 0
        cat_response.total_value = float(total_value) if total_value else 0
        cat_response.avg_value = float(avg_value) if avg_value else 0
        categories_with_stats.append(cat_response)
    
    return categories_with_stats


@router.get("/roots", response_model=List[CategoryResponse])
async def get_root_categories(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Получение корневых категорий (без родителя).
    """

    result = await db.execute(
        select(Category)
        .where(Category.parent_id.is_(None))
        .order_by(Category.name)
    )

    categories = result.scalars().all()
    return categories


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]
):
    """
    Создание новой категории
    """

    # Проверяем уникальность названия
    result = await db.execute(
        select(Category).where(Category.name == category_in.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория с таким названием уже существует"
        )
    
    # Проверяем существование родительской категории, если указана
    if category_in.parent_id:
        result = await db.execute(
            select(Category).where(Category.id == category_in.parent_id)
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Родительская категория не найдена"
            )
    
    category = Category(**category_in.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category


@router.get("/{category_id}", response_model=CategoryWithChildrenResponse)
async def get_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    include_children: bool = Query(True, description="Включить дочерние категории"),
    include_assets: bool = Query(False, description="Включить список имущества")
):
    """
    Получение категории по ID
    """

    query = select(Category).where(Category.id == category_id)
    
    if include_children:
        query = query.options(selectinload(Category.subcategories))
    
    if include_assets:
        query = query.options(selectinload(Category.assets))
    
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    return category


@router.get("/{category_id}/assets")
async def get_category_assets(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Получение списка имущества в категории.
    """

    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    from app.api.schemas.asset import AssetListResponse
    
    result = await db.execute(
        select(Asset)
        .where(Asset.category_id == category_id)
        .offset(skip)
        .limit(limit)
        .order_by(Asset.created_at.desc())
    )
    assets = result.scalars().all()
    
    return assets


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]  # Только для админов
):
    """
    Обновление категории.
    """

    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    if category_in.name and category_in.name != category.name:
        result = await db.execute(
            select(Category).where(Category.name == category_in.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория с таким названием уже существует"
            )
    
    if category_in.parent_id == category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория не может быть родителем самой себя"
        )
    
    if category_in.parent_id:
        result = await db.execute(
            select(Category).where(Category.id == category_in.parent_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Родительская категория не найдена"
            )
    
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)],
    force: bool = Query(False, description="Принудительное удаление (переносит имущество в 'Без категории')")
):
    """
    Удаление категории.
    """

    result = await db.execute(
        select(Category)
        .where(Category.id == category_id)
        .options(selectinload(Category.subcategories))
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    if force:
        if category.subcategories:
            for subcat in category.subcategories:
                subcat.parent_id = category.parent_id
                db.add(subcat)
        
        await db.execute(
            update(Asset)
            .where(Asset.category_id == category_id)
            .values(category_id=None)
        )
        
        await db.delete(category)
        
    else:
        if category.subcategories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить категорию с подкатегориями. Используйте force=true для принудительного удаления"
            )
        
        result = await db.execute(
            select(Asset).where(Asset.category_id == category_id).limit(1)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить категорию с имуществом. Используйте force=true для принудительного удаления"
            )

        await db.delete(category)
    
    await db.commit()


@router.post("/{category_id}/merge")
async def merge_categories(
    category_id: int,
    target_category_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)],  # Только для админов
    delete_source: bool = Query(True, description="Удалить исходную категорию после объединения")
):
    """
    Объединение двух категорий.
    """

    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    source_category = result.scalar_one_or_none()
    
    if not source_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Исходная категория не найдена"
        )
    
    result = await db.execute(
        select(Category).where(Category.id == target_category_id)
    )
    target_category = result.scalar_one_or_none()
    
    if not target_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Целевая категория не найдена"
        )
    
    if category_id == target_category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя объединить категорию с самой собой"
        )
    
    if source_category.subcategories:
        for subcat in source_category.subcategories:
            subcat.parent_id = target_category_id
            db.add(subcat)
    
    await db.execute(
        update(Asset)
        .where(Asset.category_id == category_id)
        .values(category_id=target_category_id)
    )
    
    if delete_source:
        await db.delete(source_category)
    
    await db.commit()
    
    return {
        "message": f"Категории объединены",
        "source_category": source_category.name,
        "target_category": target_category.name,
        "source_deleted": delete_source
    }


@router.get("/{category_id}/path")
async def get_category_path(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    """
    Получение полного пути к категории.
    """
    path = []
    current_id = category_id
    
    while current_id:
        result = await db.execute(
            select(Category).where(Category.id == current_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            break
        
        path.insert(0, {
            "id": category.id,
            "name": category.name
        })
        
        current_id = category.parent_id
    
    return path


@router.get("/stats/summary")
async def get_categories_summary(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(deps.get_current_admin)]  # Только для админов
):
    """
    Получение сводной статистики по категориям.
    """

    result = await db.execute(select(func.count()).select_from(Category))
    total_categories = result.scalar()
    
    result = await db.execute(
        select(func.count()).select_from(Category).where(Category.parent_id.is_(None))
    )
    root_categories = result.scalar()
    
    result = await db.execute(
        select(
            Category.name,
            func.count(Asset.id).label('assets_count')
        )
        .join(Asset, isouter=True)
        .group_by(Category.id)
        .order_by(func.count(Asset.id).desc())
        .limit(10)
    )
    top_categories = [
        {"name": name, "assets_count": count}
        for name, count in result.all()
    ]
    
    return {
        "total_categories": total_categories,
        "root_categories": root_categories,
        "top_categories_by_assets": top_categories
    }