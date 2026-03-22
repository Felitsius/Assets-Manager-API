from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime

class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=300)
    building: Optional[str] = Field(None, max_length=100)
    floor: Optional[str] = Field(None, max_length=50)
    room: Optional[str] = Field(None, max_length=50)

class LocationCreate(LocationBase):
    parent_id: Optional[int] = Field(None, ge=1)

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=300)
    building: Optional[str] = Field(None, max_length=100)
    floor: Optional[str] = Field(None, max_length=50)
    room: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[int] = Field(None, ge=1)

class LocationResponse(LocationBase):
    id: int
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class LocationWithChildrenResponse(LocationResponse):
    children: List['LocationWithChildrenResponse'] = []
    
    model_config = ConfigDict(from_attributes=True)

class LocationWithStatsResponse(LocationResponse):
    assets_count: int = 0
    total_value: Optional[float] = 0
    
    model_config = ConfigDict(from_attributes=True)

