from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snapchat_accounts = relationship("SnapchatAccount", back_populates="agency", cascade="all, delete")
    proxies = relationship("Proxy", back_populates="agency", cascade="all, delete")
    users = relationship("User", back_populates="agency", cascade="all, delete")
    chatbots = relationship("ChatBot", back_populates="agency", cascade="all, delete")
    executions = relationship("Execution", back_populates="agency", cascade="all, delete")
    jobs = relationship("Job", back_populates="agency", cascade="all, delete")
    workflows = relationship("Workflow", back_populates="agency", cascade="all, delete")
    models = relationship("Model", back_populates="agency", cascade="all, delete")
    subscription = relationship("Subscription", back_populates="agency", uselist=False, cascade="all, delete")
