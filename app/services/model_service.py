from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.schemas.model import Model


class ModelService:
    @staticmethod
    def get_all_models(
        db: Session,
        agency_id:int,
        name: Optional[str] = None,
    ) -> List[Model]:
        query = db.query(Model).filter(Model.agency_id == agency_id)
        if name:
            query = query.filter(Model.name.ilike(f"%{name}%"))
        return query.all()

    @staticmethod
    def get_model_by_id(db: Session, model_id: int) -> Optional[Model]:
        return db.query(Model).filter(Model.id == model_id).first()

    @staticmethod
    def create_model(db: Session, agency_id:int, payload: dict) -> Model:
        payload["agency_id"] = agency_id
        model = Model(**payload)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def update_model(db: Session, model_id: int, payload: dict) -> Model:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise ValueError("Model not found.")
        for key, value in payload.items():
            setattr(model, key, value)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def partially_update_model(db: Session, model_id: int, payload: dict) -> Model:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise ValueError("Model not found.")
        for key, value in payload.items():
            setattr(model, key, value)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def delete_model(db: Session, model_id: int) -> bool:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            return False
        db.delete(model)
        db.commit()
        return True
