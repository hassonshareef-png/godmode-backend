from sqlalchemy import Column, Integer, String
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tier = Column(String, default="god")  # god / universe / director
    reset_token = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True, index=True)
