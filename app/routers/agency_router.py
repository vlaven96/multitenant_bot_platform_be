from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.dtos.agency_dtos import AgencyCreate, AgencyResponse
from app.services.agency_service import AgencyService
from app.utils.security import hash_password

router = APIRouter(
    prefix="/agencies",  # Keeps original prefix
    tags=["agencies"]
)

@router.get("/", response_model=list[AgencyResponse])
def get_all_agencies(db: Session = Depends(get_db)):
    """
    Retrieves all agencies.
    """
    return AgencyService.get_all_agencies(db)


@router.post("/", response_model=AgencyResponse)
def create_agency(agency_data: AgencyCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)):
    """
    Creates a new agency with an auto-generated admin account.
    """
    try:
        # All invitation logic is encapsulated in the static method
        agency = AgencyService.create_agency_with_invitation(db, agency_data, background_tasks, request)
        return agency
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agency_id}", response_model=AgencyResponse)
def get_agency(agency_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single agency by its ID.
    """
    agency = AgencyService.get_agency_by_id(db, agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found.")
    return agency
