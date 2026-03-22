from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.api.core.database import Base


class MovementType(str, enum.Enum):
    TRANSFER = "transfer"           # Перемещение
    ASSIGN = "assign"               # Выдача сотруднику
    RETURN = "return"               # Возврат от сотрудника
    REPAIR = "repair"               # Отправка в ремонт
    REPAIR_RETURN = "repair_return" # Возврат из ремонта
    DECOMMISSION = "decommission"    # Списание


class Movement(Base):
    """Класс для модели таблицы перемещения имущества в БД"""

    __tablename__ = "movements"
    
    id = Column(Integer, primary_key=True, index=True)
    
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    
    movement_type = Column(Enum(MovementType), nullable=False)
    
    from_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    
    from_assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    to_assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    initiated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    
    reason = Column(Text, nullable=True)
    document_number = Column(String, nullable=True)
    
    movement_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_return_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    asset = relationship("Asset", back_populates="movements")
    
    from_location = relationship(
        "Location", 
        foreign_keys=[from_location_id],
        back_populates="movements_from"
    )
    
    to_location = relationship(
        "Location", 
        foreign_keys=[to_location_id],
        back_populates="movements_to"
    )
    
    initiated_by = relationship(
        "User", 
        foreign_keys=[initiated_by_id]
    )