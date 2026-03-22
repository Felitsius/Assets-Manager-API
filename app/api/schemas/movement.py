from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date
from app.api.models.movement import MovementType

class MovementBase(BaseModel):
    movement_type: MovementType
    reason: Optional[str] = None
    document_number: Optional[str] = None
    expected_return_date: Optional[date] = None

class MovementCreate(MovementBase):
    asset_id: int
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    from_assignee_id: Optional[int] = None
    to_assignee_id: Optional[int] = None

class MovementResponse(MovementBase):
    id: int
    asset_id: int
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    from_assignee_id: Optional[int] = None
    to_assignee_id: Optional[int] = None
    initiated_by_id: int
    movement_date: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)