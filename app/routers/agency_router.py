from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.dtos.agency_dtos import AgencyCreate, AgencyResponse, AgencyCreateRequest
from app.dtos.user_invite_request import UserInviteRequest
from app.services.agency_service import AgencyService
from app.utils.security import hash_password, get_agency_id, get_admin_user, get_global_admin

router = APIRouter(
    prefix="/agencies",  # Keeps original prefix
    tags=["agencies"]
)


@router.get("/", response_model=list[AgencyResponse])
def get_all_agencies(db: Session = Depends(get_db), global_admin=Depends(get_global_admin)):
    """
    Retrieves all agencies.
    """
    return AgencyService.get_all_agencies(db)


@router.post("/", response_model=AgencyResponse)
def create_agency(agency_data: AgencyCreate,
                  background_tasks: BackgroundTasks,
                  db: Session = Depends(get_db)):
    """
    Creates a new agency with an auto-generated admin account.
    """
    try:
        # All invitation logic is encapsulated in the static method
        agency = AgencyService.create_agency_with_invitation(db, agency_data, background_tasks)
        return agency
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# @router.post("/", response_model=AgencyResponse)
# def create_agency(agency_data: AgencyCreateRequest,
#                   background_tasks: BackgroundTasks,
#                   db: Session = Depends(get_db)):
#     """
#     Creates a new agency with an auto-generated admin account.
#     """
#     try:
#         # All invitation logic is encapsulated in the static method
#         agency = AgencyService.create_agency(db, agency_data)
#         return agency
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.post("/invite_agency", response_model=dict)
def invite_agency(
        invite_request: UserInviteRequest,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_global_admin),
):
    AgencyService.invite_user_to_create_agency(db, invite_request.email)
    return {"detail": "Invitation to create agency sent successfully."}

@router.get("/{agency_id}", response_model=AgencyResponse)
def get_agency(db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id),
               current_user: dict = Depends(get_admin_user)):
    """
    Retrieves a single agency by its ID.
    """
    agency = AgencyService.get_agency_by_id(db, agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found.")
    return agency


@router.post("/{agency_id}/invite", response_model=dict)
def invite_user_to_agency(
        invite_request: UserInviteRequest,
        db: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id),
        current_user: dict = Depends(get_admin_user),
):
    """
    Invites a user to the agency via email.
    """
    try:
        # The invite_user_to_agency method should handle sending an invitation email,
        # creating a pending invitation record, etc.
        AgencyService.invite_user_to_agency(db, agency_id, invite_request.email)
        return {"detail": "Invitation sent successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


