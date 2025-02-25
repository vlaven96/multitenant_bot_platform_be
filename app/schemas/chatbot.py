from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

from app.models.chat_bot_type_enum import ChatBotTypeEnum


class ChatBot(Base):
    __tablename__ = 'chatbot'

    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    type = Column(Enum(ChatBotTypeEnum, name="chatbot_type_enum"), nullable=False)
    token = Column(String, unique=True, nullable=False)

    # One-to-Many relationship with SnapchatAccount
    snapchat_accounts = relationship("SnapchatAccount", back_populates="chat_bot")
    agency = relationship("Agency", back_populates="chatbots")
