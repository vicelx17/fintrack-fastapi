from sqlalchemy import Integer, String, Column, Boolean
from sqlalchemy.orm import relationship

from app.core import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String,nullable=False)
    last_name = Column(String,nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    categories = relationship("Category", back_populates="user", passive_deletes=True)
    budgets = relationship("Budget", back_populates="user", passive_deletes=True)