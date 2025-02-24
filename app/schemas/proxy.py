from sqlalchemy import Column, Integer, String, ForeignKey, Integer, UniqueConstraint
from app.database import Base
from sqlalchemy.orm import relationship

class Proxy(Base):
    __tablename__ = 'proxy'
    
    id = Column(Integer, primary_key=True)
    proxy_username = Column(String, nullable=False)
    proxy_password = Column(String, nullable=False)
    host = Column(String, nullable=False)
    port = Column(String, default= "44444", nullable=False)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    # One-to-Many: A Proxy can exist without any accounts

    __table_args__ = (
        UniqueConstraint('proxy_username', 'proxy_password', 'host', 'port', name='uq_proxy_combination'),
    )

    snapchat_accounts = relationship(
        "SnapchatAccount",
        back_populates="proxy",
        foreign_keys="SnapchatAccount.proxy_id",  # Explicitly define the foreign key
        cascade="save-update, merge"
    )

    agency = relationship("Agency", back_populates="proxy")
