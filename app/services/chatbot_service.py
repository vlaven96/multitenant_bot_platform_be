from sqlalchemy.orm import Session
from typing import List

from app.dtos.chatbot_dtos import ChatBotCreate, ChatBotUpdate
from app.schemas.chatbot import ChatBot


class ChatBotService:
    @staticmethod
    def get_all_chatbots(db: Session) -> List[ChatBot]:
        return db.query(ChatBot).all()

    @staticmethod
    def create_chatbot(db: Session, chatbot_data: ChatBotCreate) -> ChatBot:
        chatbot = ChatBot(**chatbot_data.dict())
        db.add(chatbot)
        db.commit()
        db.refresh(chatbot)
        return chatbot

    @staticmethod
    def update_chatbot(db: Session, chatbot_id: int, chatbot_data: ChatBotUpdate) -> ChatBot:
        chatbot = db.query(ChatBot).filter(ChatBot.id == chatbot_id).first()
        if not chatbot:
            return None

        for key, value in chatbot_data.dict(exclude_unset=True).items():
            setattr(chatbot, key, value)

        db.commit()
        db.refresh(chatbot)
        return chatbot

    @staticmethod
    def partially_update_chatbot(db: Session, chatbot_id: int, chatbot_data: ChatBotUpdate) -> ChatBot:
        return ChatBotService.update_chatbot(db, chatbot_id, chatbot_data)

    @staticmethod
    def delete_chatbot(db: Session, chatbot_id: int) -> bool:
        """
        Deletes a chatbot by its ID.

        :param db: Database session.
        :param chatbot_id: ID of the chatbot to delete.
        :return: True if deleted, False if not found.
        """
        chatbot = db.query(ChatBot).filter(ChatBot.id == chatbot_id).first()
        if not chatbot:
            return False

        db.delete(chatbot)
        db.commit()
        return True
