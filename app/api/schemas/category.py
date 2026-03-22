from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название категории")
    description: Optional[str] = Field(None, max_length=500, description="Описание категории")

class CategoryCreate(CategoryBase):
    parent_id: Optional[int] = Field(None, ge=1, description="ID родительской категории")

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Название категории")
    description: Optional[str] = Field(None, max_length=500, description="Описание категории")
    parent_id: Optional[int] = Field(None, ge=1, description="ID родительской категории")

class CategoryResponse(CategoryBase):
    id: int
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CategoryWithChildrenResponse(CategoryResponse):
    children: List['CategoryWithChildrenResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)

class CategoryWithStatsResponse(CategoryResponse):
    assets_count: int = 0
    total_value: float = 0
    avg_value: float = 0
    
    model_config = ConfigDict(from_attributes=True)

class CategoryTreeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List['CategoryTreeResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)

CategoryWithChildrenResponse.model_rebuild()
CategoryTreeResponse.model_rebuild()