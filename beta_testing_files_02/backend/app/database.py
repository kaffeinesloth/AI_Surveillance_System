from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# SQLite chi cho 1 writer tai 1 thoi diem -> check_same_thread=False de dung
# duoc voi FastAPI (nhieu request/threads), nhung van chi co 1 writer thuc su.
# Du cho quy mo 1-vai camera cua do an - xem lai neu sau nay chay nhieu camera
# dong thoi ghi alert cung luc (luc do moi can chuyen sang PostgreSQL).
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency cho FastAPI - moi request duoc 1 session rieng, tu dong dong lai."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
