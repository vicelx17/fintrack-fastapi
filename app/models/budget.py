from datetime import datetime, timezone, date

from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, String, Date

from sqlalchemy.orm import relationship

from app.core import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(Date, default=date.today(), nullable=False)
    end_date = Column(Date, default=date.today(), nullable=False)
    period = Column(String, default="monthly", nullable=False)
    alert_threshold = Column(Integer, default=80, nullable=False)

    # FK
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    #Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")