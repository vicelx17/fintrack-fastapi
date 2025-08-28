from datetime import datetime, timezone


from sqlalchemy import Column, Integer, ForeignKey, Float, String, TIMESTAMP
from sqlalchemy.orm import relationship

from app.core import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    date = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")