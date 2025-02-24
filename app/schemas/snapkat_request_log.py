from app.database import Base
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from datetime import datetime

class SnapkatRequestLog(Base):
    __tablename__ = "snapkat_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    method = Column(String, nullable=False)
    headers = Column(JSON, nullable=True)
    payload = Column(Text, nullable=True)
    params = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)