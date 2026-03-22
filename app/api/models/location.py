from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.api.core.database import Base


class Location(Base):
    """Класс для модели таблицы месторасположения имущества в БД"""
    
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    address = Column(String, nullable=True)
    building = Column(String, nullable=True)
    floor = Column(String, nullable=True)
    room = Column(String, nullable=True)
    
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    parent = relationship("Location", remote_side=[id], backref="sublocations")
    assets = relationship("Asset", back_populates="location")
    movements_from = relationship("Movement", foreign_keys="Movement.from_location_id", back_populates="from_location")
    movements_to = relationship("Movement", foreign_keys="Movement.to_location_id", back_populates="to_location")