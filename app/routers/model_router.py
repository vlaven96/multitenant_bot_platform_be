from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.model import Model
from app.services.model_service import ModelService
from app.dtos.model_response import ModelResponse
from app.utils.security import get_current_user, get_agency_id

router = APIRouter(
    prefix="/models",
    tags=["models"]
)


@router.get("/", response_model=List[ModelResponse])
def get_all_models(
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
        name: Optional[str] = Query(None, description="Filter by model name"),
):
    """
    Retrieves all models with optional filters.
    """
    return ModelService.get_all_models(db=db, agency_id=agency_id, name=name)


@router.get("/{model_id}", response_model=ModelResponse)
def get_model_by_id(
        model_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
):
    """
    Retrieves a single model by its ID.
    """
    model = ModelService.get_model_by_id(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found.")
    return model


@router.post("/", response_model=ModelResponse)
def create_model(
        payload: dict = Body(..., description="JSON payload to create a new model."),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
):
    """
    Creates a new model.
    """
    try:
        return ModelService.create_model(db, agency_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{model_id}", response_model=ModelResponse)
def update_model(
        model_id: int,
        payload: dict = Body(..., description="JSON payload to update the model."),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
):
    """
    Updates a model by its ID.
    """
    try:
        return ModelService.update_model(db, model_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{model_id}", response_model=ModelResponse)
def partially_update_model(
        model_id: int,
        payload: dict = Body(..., description="JSON payload to partially update the model."),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
):
    """
    Partially updates a model by its ID.
    """
    try:
        return ModelService.partially_update_model(db, model_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{model_id}", response_model=dict)
def delete_model(
        model_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
        agency_id: int = Depends(get_agency_id),
):
    """
    Deletes a model by its ID.
    """
    if not ModelService.delete_model(db, model_id):
        raise HTTPException(status_code=404, detail="Model not found.")
    return {"message": "Model deleted successfully."}
