from fastapi import APIRouter, Depends, HTTPException, Body, Header
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.dtos.proxy_response import ProxyResponse
from app.database import get_db
from app.services.proxy_service import ProxyService
from app.utils.security import get_current_user, authenticate_user_or_api_key, get_agency_id

router = APIRouter(
    prefix="/proxies",
    tags=["proxies"]
)


@router.get("/", response_model=List[ProxyResponse])
def get_all_proxies(
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all proxies from the database.
    """
    return ProxyService.get_all_proxies(db, agency_id)

@router.get("/least_used", response_model=ProxyResponse)
def get_least_used_proxy(
    max_associations: Optional[int] = None,
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Retrieves the proxy with the least number of SnapchatAccount associations.
    Optionally, a maximum number of allowed associations can be specified.
    If no proxy meets the criteria, a 404 error is returned.
    """
    proxy = ProxyService.get_least_used_proxy(db, agency_id, max_associations)
    if not proxy:
        raise HTTPException(status_code=404, detail="No suitable proxy found.")
    return proxy

@router.get("/{proxy_id}", response_model=ProxyResponse)
def get_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    agency_id: int = Depends(get_agency_id),
):
    """
    Retrieves a specific proxy by its ID.
    """
    proxy = ProxyService.get_proxy_by_id(db, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found.")
    return proxy

@router.post("/", response_model=List[ProxyResponse])
def create_proxies(
    payload: dict = Body(..., description="JSON payload with a 'data' field containing proxy details."),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    agency_id: int = Depends(get_agency_id),
):
    """
    Creates new proxies from a JSON payload.
    The payload should be a list of proxy objects with fields: proxy_username, proxy_password, host, port.
    """
    try:
        return ProxyService.create_proxies(db, agency_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{proxy_id}", response_model=dict)
def delete_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    agency_id: int = Depends(get_agency_id),
):
    """
    Deletes a proxy by its ID.
    """
    proxy = ProxyService.get_proxy_by_id(db, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found.")

    ProxyService.delete_proxy(db, proxy_id)
    return {"message": "Proxy deleted successfully."}
