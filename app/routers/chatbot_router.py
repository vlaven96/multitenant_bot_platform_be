from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dtos.chatbot_dtos import ChatBotResponse, ChatBotCreate, ChatBotUpdate
from app.services.chatbot_service import ChatBotService
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/chatbots",
    tags=["chatbots"]
)

@router.get("/", response_model=List[ChatBotResponse])
def get_all_chatbots(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all chatbots.
    """
    return ChatBotService.get_all_chatbots(db)


@router.post("/", response_model=ChatBotResponse)
def create_chatbot(
    chatbot_data: ChatBotCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new chatbot.
    """
    try:
        return ChatBotService.create_chatbot(db, chatbot_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{chatbot_id}", response_model=ChatBotResponse)
def update_chatbot(
    chatbot_id: int,
    chatbot_data: ChatBotUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Updates a chatbot by its ID.
    """
    chatbot = ChatBotService.update_chatbot(db, chatbot_id, chatbot_data)
    if not chatbot:
        raise HTTPException(status_code=404, detail="ChatBot not found.")
    return chatbot


@router.patch("/{chatbot_id}", response_model=ChatBotResponse)
def partially_update_chatbot(
    chatbot_id: int,
    chatbot_data: ChatBotUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Partially updates a chatbot by its ID.
    """
    chatbot = ChatBotService.partially_update_chatbot(db, chatbot_id, chatbot_data)
    if not chatbot:
        raise HTTPException(status_code=404, detail="ChatBot not found.")
    return chatbot

@router.delete("/{chatbot_id}", response_model=dict)
def delete_chatbot(
    chatbot_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a chatbot by its ID.
    """
    try:
        is_deleted = ChatBotService.delete_chatbot(db, chatbot_id)
        if not is_deleted:
            raise HTTPException(status_code=404, detail="ChatBot not found.")
        return {"message": "ChatBot deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete ChatBot: {str(e)}")