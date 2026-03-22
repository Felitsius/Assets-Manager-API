from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from app.api.models.asset import AssetStatus, AssetCondition


class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    inventory_number: str = Field(..., min_length=1, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    currency: str = "RUB"
    status: AssetStatus = AssetStatus.NEW
    condition: AssetCondition = AssetCondition.GOOD
    notes: Optional[str] = None


class AssetCreate(AssetBase):
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    assignee_id: Optional[int] = None
    
    @field_validator('inventory_number')
    @classmethod
    def validate_inventory_number(cls, v):
        # Можно добавить кастомную валидацию формата инвентарного номера
        if not v.strip():
            raise ValueError('Inventory number cannot be empty')
        return v


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    status: Optional[AssetStatus] = None
    condition: Optional[AssetCondition] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    assignee_id: Optional[int] = None
    current_value: Optional[float] = None
    notes: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    assignee_id: Optional[int] = None
    registered_by_id: int
    current_value: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AssetWithRelationsResponse(AssetResponse):
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    assignee_name: Optional[str] = None
    registrar_name: Optional[str] = None

class AssetListResponse(BaseModel):
    id: int
    name: str
    inventory_number: str
    status: AssetStatus
    condition: AssetCondition
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)