from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SnapchatAccountStats(Base):
    __tablename__ = 'snapchat_account_stats'

    id = Column(Integer, primary_key=True)
    snapchat_account_id = Column(Integer, ForeignKey('snapchat_account.id', ondelete="CASCADE"), unique=True, nullable=False)

    # Statistics fields
    total_conversations = Column(Integer, default=0, nullable=False)
    chatbot_conversations = Column(Integer, default=0, nullable=False)
    conversations_charged = Column(Integer, default=0, nullable=False)
    cta_conversations = Column(Integer, default=0, nullable=False)
    cta_shared_links = Column(Integer, default=0, nullable=False)
    conversions_from_cta_links = Column(Integer, default=0, nullable=False)
    total_conversions = Column(Integer, default=0, nullable=False)
    quick_ads_sent = Column(Integer, default=0, nullable=False)
    total_executions = Column(Integer, default=0, nullable=False)
    successful_executions = Column(Integer, default=0, nullable=False)
    rejected_total = Column(Integer, default=0, nullable=False)
    generated_leads = Column(Integer, default=0, nullable=False)
    # Relationship back to SnapchatAccount
    snapchat_account = relationship("SnapchatAccount", back_populates="stats", uselist=False)

