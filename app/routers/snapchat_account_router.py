from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Union

from app.dtos.bulk_update_payload import BulkUpdatePayload
from app.dtos.snapchat_account_edit_response import SnapchatAccountEditResponse
from app.dtos.snapchat_account_response import SnapchatAccountResponse, SnapchatAccountResponseV2
from app.dtos.snapchat_account_simple_response import SnapchatAccountSimpleResponse
from app.dtos.statistics.snapchat_account_stats_response import SnapchatAccountStatsDTO, SnapchatAccountTimelineStatisticsDTO
from app.models.account_status_enum import AccountStatusEnum
from app.database import get_db
from app.services.snapchat_account_service import SnapchatAccountService
from app.services.snapchat_account_statistics_service import SnapchatAccountStatisticsService
from app.utils.security import get_current_user, authenticate_user_or_api_key, get_agency_id

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"]
)

@router.get("/", response_model=Union[List[SnapchatAccountResponse], List[SnapchatAccountResponseV2]])
def get_all_accounts(
        agency_id: int = Depends(get_agency_id),
        db: Session = Depends(get_db),
        auth: str = Depends(authenticate_user_or_api_key),
        x_api_key: Optional[str] = Header(None),
        username: Optional[str] = Query(None, description="Filter by username"),
        creation_date_from: Optional[datetime] = Query(None, description="Filter accounts created after this date"),
        creation_date_to: Optional[datetime] = Query(None, description="Filter accounts created before this date"),
        has_proxy: Optional[bool] = Query(None, description="Filter accounts with/without a proxy"),
        has_device: Optional[bool] = Query(None, description="Filter accounts with/without a device"),
        has_cookies: Optional[bool] = Query(None, description="Filter accounts with/without cookies"),
        statuses: Optional[List[AccountStatusEnum]] = Query(None, description="Filter accounts by multiple statuses"),
        include_executions: bool = Query(False, description="Include account_executions or not?"),
        has_quick_adds: bool = Query(False, description="Include uick_adds or not?"),
        page: Optional[int] = Query(None, description="Page number for pagination (optional, default: None)"),
        page_size: Optional[int] = Query(None, description="Page size for pagination (optional, default: None)"),
):
    snapchat_accounts = SnapchatAccountService.get_all_accountsV2(
        db=db,
        agency_id=agency_id,
        username=username,
        creation_date_from=creation_date_from,
        creation_date_to=creation_date_to,
        has_proxy=has_proxy,
        has_device=has_device,
        has_cookies=has_cookies,
        statuses=statuses,
        page = page,
        page_size = page_size,
        include_executions = include_executions,
        has_quick_adds= has_quick_adds
    )
    if not include_executions:
        # We'll produce a list of SnapchatAccountLiteResponse
        lite_response = []
        for acct in snapchat_accounts:
            # Fill fields as needed
            lite_response.append(SnapchatAccountResponseV2.from_orm(acct))
        return lite_response
    else:
        # We'll produce a list of SnapchatAccountFullResponse
        full_response = []
        for acct in snapchat_accounts:
            # Make sure `account_executions` is actually loaded or set
            full_response.append(SnapchatAccountResponse.from_orm(acct))
        return full_response

@router.get("/candidates-for-termination", response_model=List[SnapchatAccountSimpleResponse])
def get_accounts_for_termination(
    agency_id: int = Depends(get_agency_id),
    db: Session = Depends(get_db),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Retrieves all accounts that are candidates for termination based on specified filters.
    """
    try:
        accounts = SnapchatAccountService.get_accounts_for_termination(
            db=db,
            agency_id=agency_id
        )
        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found for termination.")
        return accounts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.patch("/terminate", response_model=dict)
def terminate_accounts(
    agency_id: int = Depends(get_agency_id),
    account_ids: List[int] = Body(..., description="List of account IDs to be terminated."),
    db: Session = Depends(get_db),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: str = Header(None, description="API key for authorization"),
):
    """
    Marks all provided accounts as TERMINATED.
    """
    if not account_ids:
        raise HTTPException(status_code=400, detail="Account IDs list cannot be empty.")

    try:
        updated_count = SnapchatAccountService.terminate_accounts(db, account_ids)
        return {"message": f"{updated_count} accounts have been terminated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.patch("/bulk-update")
def bulk_update_accounts(
    payload: BulkUpdatePayload,  # automatically parses JSON into this Pydantic model
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Bulk updates multiple SnapchatAccounts based on the fields provided.
    Example payload:
    {
      "account_ids": [209, 321, 380],
      "status": "GOOD_STANDING",
      "tags_to_add": ["GROUP_6_30"],
      "tags_to_remove": ["GROUP_3_30"],
      "model_id": 2,
      "chat_bot_id": 1
    }
    """
    try:
        if not payload.account_ids:
            raise HTTPException(status_code=400, detail="No account IDs provided.")

        updated_count = SnapchatAccountService.bulk_update_accounts(
            db=db,
            account_ids=payload.account_ids,
            status=payload.status,
            tags_to_add=payload.tags_to_add,
            tags_to_remove=payload.tags_to_remove,
            model_id=payload.model_id,
            chat_bot_id=payload.chat_bot_id,
        )

        return {
            "message": f"{updated_count} account(s) successfully updated."
        }

    except ValueError as e:
        # e.g. if status is invalid or no accounts found
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{account_id}", response_model=Union[SnapchatAccountResponse, SnapchatAccountResponseV2])
def get_account(
    account_id: int,
    include_executions: bool = Query(False, description="Include account_executions or not?"),
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves a Snapchat account by its ID.
    """
    account = SnapchatAccountService.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Snapchat account not found.")
    if include_executions:
        # Construct and return the full response including executions
        return SnapchatAccountResponse.from_orm(account)
    else:
        # Construct and return a lighter version without executions
        return SnapchatAccountResponseV2.from_orm(account)


@router.patch("/{account_id}", response_model=SnapchatAccountResponse)
def update_account(
    account_id: int,
    payload: dict = Body(..., description="JSON payload with fields to update."),
    db: Session = Depends(get_db),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
    agency_id: int = Depends(get_agency_id),
):
    """
    Updates a Snapchat account by its ID with the provided fields.
    """
    try:
        updated_account = SnapchatAccountService.update_account(db, account_id, payload)
        return updated_account
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/", response_model=List[SnapchatAccountResponse])
def create_accounts(
    payload: dict = Body(..., description="JSON payload with a 'data' field containing account details."),
    account_source: Optional[str] = Body(None, description="Optional account source."),
    model_id: Optional[int] = Body(None, description="Optional model ID."),
    chatbot_id: Optional[int] = Body(None, description="Optional chatbot ID."),
    workflow_id: Optional[int] = Body(None, description="Optional workflow ID."),
    pattern: Optional[str] = Body(None, description="Optional pattern."),
    trigger_execution: bool = Body(False, description="Boolean flag to trigger execution."),
    db: Session = Depends(get_db),
    auth: str = Depends(authenticate_user_or_api_key),
    agency_id: int = Depends(get_agency_id),
    x_api_key: Optional[str] = Header(None),
):
    """
    Creates Snapchat accounts from a large string input.
    """
    try:
        data = payload.get("data")
        if not isinstance(data, str):
            raise ValueError("Invalid payload. 'data' field must be a string.")
        return SnapchatAccountService.create_accounts_from_string(db, agency_id, data, account_source, model_id, chatbot_id, workflow_id, trigger_execution, pattern)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{username}/cookies", response_model=SnapchatAccountResponse)
def create_cookies_for_account(
        username: str,
        cookies_payload: dict = Body(...,
                                     description="JSON payload containing cookies data."),
        db: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id),
        auth: str = Depends(authenticate_user_or_api_key),
        x_api_key: Optional[str] = Header(None),
):
    """
    Creates cookies and attaches it to the specified Snapchat account based on the username.
    """
    try:
        if not cookies_payload or not cookies_payload.get("cookies"):
            raise HTTPException(status_code=400, detail="Cookies payload is required.")

        account = SnapchatAccountService.create_and_attach_cookies(db, username, cookies_payload.get("cookies"))

        if not account:
            raise HTTPException(status_code=404, detail="Account not found.")

        return account

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/by-username/{username}", response_model=SnapchatAccountResponse)
def update_account_by_username(
    username: str,
    payload: dict = Body(..., description="JSON payload with fields to update."),
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Updates a Snapchat account by its username with the provided fields.
    """
    try:
        updated_account = SnapchatAccountService.update_account_by_username(db, username, payload)
        if not updated_account:
            raise HTTPException(status_code=404, detail="Snapchat account not found.")
        return updated_account
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/by-username/{username}", response_model=SnapchatAccountResponse)
def get_account_by_username(
    username: str,
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Fetches a Snapchat account by its username.
    """
    try:
        snapchat_account = SnapchatAccountService.get_account_by_username(db, username)
        if not snapchat_account:
            raise HTTPException(status_code=404, detail="Snapchat account not found.")
        return snapchat_account
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



@router.get("/{account_id}/edit", response_model=SnapchatAccountEditResponse)
def get_account_edit_data(
    account_id: int,
    db: Session = Depends(get_db),
    agency_id: int = Depends(get_agency_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all necessary data for the edit page of a Snapchat account.
    """
    try:
        edit_data = SnapchatAccountService.get_account_edit_data(db, account_id)
        return edit_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/statuses/list", response_model=list[str])
def retrieve_snapchat_account_statuses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),agency_id: int = Depends(get_agency_id),):
    """
    Endpoint to retrieve all unique statuses from the SnapchatAccount table.
    """
    return SnapchatAccountService.get_snapchat_account_statuses(db)

@router.get("/sources/list", response_model=list[str])
def retrieve_snapchat_account_sources(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), agency_id: int = Depends(get_agency_id),):
    """
    Endpoint to retrieve all unique statuses from the SnapchatAccount table.
    """
    return SnapchatAccountService.get_snapchat_account_sources(db, agency_id)

@router.get("/{account_id}/statistics", response_model=SnapchatAccountStatsDTO)
def get_user_statistics(account_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), agency_id: int = Depends(get_agency_id),):
    """
    Endpoint to retrieve user statistics.

    :param user_id: The ID of the user.
    :param db: The database session.
    :return: SnapchatAccountStatsDTO containing the user's statistics.
    """
    statistics_dto = SnapchatAccountStatisticsService.get_user_statistics(db, account_id)

    return statistics_dto

@router.get("/{account_id}/timeline-statistics", response_model=SnapchatAccountTimelineStatisticsDTO)
def get_user_timeline_statistics(account_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), agency_id: int = Depends(get_agency_id),):
    """
    Endpoint to retrieve user timeline statistics.

    :param user_id: The ID of the user.
    :param db: The database session.
    :return: SnapchatAccountStatsDTO containing the user's statistics.
    """
    statistics_dto = SnapchatAccountStatisticsService.get_user_timeline_statistics(db, account_id)
    return statistics_dto