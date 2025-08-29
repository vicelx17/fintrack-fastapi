from datetime import datetime, timezone


from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, String

from sqlalchemy.orm import relationship

from app.core import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    # FK
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    #Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")