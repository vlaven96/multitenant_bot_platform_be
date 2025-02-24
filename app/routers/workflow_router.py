from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dtos.workflow_dtos import WorkflowResponse, WorkflowCreateRequest, WorkflowSimplifiedResponse, \
    WorkflowUpdateRequest, WorkflowStatusUpdateRequest, WorkflowSimplifiedNameResponse
from app.dtos.workflow_snapchat_account_response import WorkflowSnapchatAccountResponse
from app.services.workflow_service import WorkflowsService
from app.utils.security import get_admin_user

router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_create: WorkflowCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to create a new workflow.
    """
    return WorkflowsService.create_workflow(db, workflow_create)


@router.get("/", response_model=List[WorkflowResponse])
def read_workflows(
    name_filter: Optional[str] = Query(None, description="Filter workflows by name"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to retrieve a list of workflows, optionally filtered by name.
    """
    return WorkflowsService.list_workflows(db, name_filter)


@router.get("/simplified", response_model=List[WorkflowSimplifiedNameResponse])
def read_workflows_simplified(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to retrieve a simplified list of workflows (id and name only).
    """
    return WorkflowsService.list_workflows_simplified(db)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def read_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to retrieve a specific workflow by its ID.
    """
    return WorkflowsService.get_workflow(db, workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to update an existing workflow's details.
    """
    return WorkflowsService.update_workflow(db, workflow_id, workflow_update)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
):
    """
    Endpoint to delete a workflow by its ID.
    """
    WorkflowsService.delete_workflow(db, workflow_id)
    return


@router.post("/{workflow_id}/restore", response_model=WorkflowResponse, status_code=status.HTTP_200_OK)
def restore_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
):
    """
    Endpoint to restore a workflow by its ID.
    """
    return WorkflowsService.restore_workflow(db, workflow_id)

@router.patch("/{workflow_id}/status", response_model=WorkflowResponse, status_code=status.HTTP_200_OK)
def update_workflow_status(
    workflow_id: int,
    status_update_request: WorkflowStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """
    Endpoint to update the status of a workflow.
    """
    return WorkflowsService.update_workflow_status(db, workflow_id, status_update_request.status_update)

@router.get("/{workflow_id}/accounts", response_model=List[WorkflowSnapchatAccountResponse])
def get_snapchat_accounts_with_steps(workflow_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to retrieve Snapchat accounts for a given workflow along with their last executed step.
    """
    return WorkflowsService.get_snapchat_accounts_with_last_executed_step(db, workflow_id)
