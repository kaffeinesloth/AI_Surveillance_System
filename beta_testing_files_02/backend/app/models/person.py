from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, default="authorized")  # authorized / staff / guest
    embedding_path = Column(String, nullable=True)  # duong dan file .npy chua vector embedding
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
