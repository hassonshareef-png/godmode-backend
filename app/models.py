from sqlalchemy import Column, Integer, String, Boolean
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tier = Column(String, default="basic")  # basic / god / universe / director
    has_god_mode = Column(Boolean, default=False)  # Purchased God Mode
    has_universe_mode = Column(Boolean, default=False)  # Purchased Universe Mode
    is_director = Column(Boolean, default=False)  # Owner with Director access
    reset_token = Column(String, nullable=True)
