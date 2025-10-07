from datetime import date

from sqlalchemy import Column, Integer, ForeignKey, Float, String, Date
from sqlalchemy.orm import relationship

from app.core import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    transaction_date = Column(Date, default=date.today(), nullable=False)
    created_at = Column(Date, default=date.today, nullable=False)
    updated_at = Column(Date, default=date.today, onupdate=date.today, nullable=False)
    type = Column(String, nullable=False)
    notes = Column(String, nullable=True)

    #FK
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    # relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")