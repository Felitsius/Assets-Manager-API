from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.api.core.database import Base


class User(Base):
    """Класс для модели таблицы пользователей в БД"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    department = Column(String, nullable=True)
    position = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    assets_assigned = relationship(
        "Asset", 
        foreign_keys="Asset.assignee_id",
        back_populates="assignee"
    )
    
    assets_registered = relationship(
        "Asset", 
        foreign_keys="Asset.registered_by_id",
        back_populates="registrar"
    )
