from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Enum, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.api.core.database import Base


class AssetStatus(str, enum.Enum):
    NEW = "new"
    IN_USE = "in_use"
    IN_REPAIR = "in_repair"
    DECOMMISSIONED = "decommissioned"
    STORED = "stored"
    LOST = "lost"


class AssetCondition(str, enum.Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"


class Asset(Base):
    """Класс для модели таблицы имущества в БД"""

    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, index=True, nullable=False)
    description = Column(Text)

    inventory_number = Column(String, unique=True, index=True, nullable=False)
    serial_number = Column(String, index=True, nullable=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    qr_code = Column(String, unique=True, nullable=True)
    
    model = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    year_of_manufacture = Column(Integer, nullable=True)

    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(Float, nullable=True)
    currency = Column(String, default="RUB")
    current_value = Column(Float, nullable=True)
    
    status = Column(Enum(AssetStatus), default=AssetStatus.NEW)
    condition = Column(Enum(AssetCondition), default=AssetCondition.GOOD)

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    registered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    warranty_until = Column(Date, nullable=True)
    last_inventory_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="assets")
    location = relationship("Location", back_populates="assets")
    
    assignee = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assets_assigned"
    )
    
    registrar = relationship(
        "User",
        foreign_keys=[registered_by_id],
        back_populates="assets_registered"
    )
    
    movements = relationship(
        "Movement",
        back_populates="asset",
        cascade="all, delete-orphan"
    )