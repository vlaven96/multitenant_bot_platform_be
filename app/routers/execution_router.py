from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.celery_tasks.executions_task import ExecutionTaskManager
from app.dtos.execution_create_request import ExecutionCreateRequest
from app.dtos.execution_response import ExecutionResponse
from app.dtos.execution_result_response import ExecutionResultResponse
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.status_enum import StatusEnum
from app.schemas.executions.execution import Execution
from app.database import get_db
from app.services.job_executor_service import JobExecutorService
from app.utils.security import get_current_user
from fastapi import Query

router = APIRouter(
    prefix="/executions",
    tags=["executions"]
)


@router.post("/", response_model=ExecutionResponse)
def create_execution(execution: ExecutionCreateRequest,
                     db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user),
                     background_tasks: BackgroundTasks = BackgroundTasks()
                     ):
    """
    Create a new execution.
    """
    username = current_user.get("sub")
    if not username:
        raise HTTPException(status_code=400, detail="User information is incomplete")
    JobExecutorService.validate_executor(execution)

    new_execution = Execution(
        type=execution.type,
        triggered_by=username,
        configuration=execution.configuration,
        status=StatusEnum.STARTED
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    ExecutionTaskManager.execute_task_celery.delay(new_execution.id, execution.accounts)

    return new_execution

@router.get("/", response_model=List[ExecutionResultResponse])
def get_all_executions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Number of records to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    username: Optional[str] = Query(None, description="Filter by Snapchat account username"),
    status: Optional[StatusEnum] = Query(None, description="Filter by AccountExecution status"),
    execution_type: Optional[ExecutionTypeEnum] = Query(None, description="Filter by Execution type"),
    job_id: Optional[int] = Query(None, description="Filter by Job"),
):
    """
      Retrieve executions with optional filtering by username and status.
      Supports pagination.
      """
    # Delegate to the service layer
    executions = JobExecutorService.get_executionsV3(
        db=db,
        limit=limit,
        offset=offset,
        username=username,
        status=status,
        execution_type=execution_type,
        job_id= job_id
    )
    return executions


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution_by_id(execution_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Retrieve a specific execution by its ID.
    """
    try:
        execution = JobExecutorService.get_execution_by_id(db, execution_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return execution

@router.get("/by_snapchat_account/{snapchat_account_id}", response_model=List[ExecutionResponse])
def get_executions_by_snapchat_account(
    snapchat_account_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Number of records to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    execution_type: Optional[ExecutionTypeEnum] = Query(None, description="Filter by Execution type"),
):
    """
    Retrieve all executions for a specific Snapchat account, paginated.
    """
    # Delegate to the service layer
    executions = JobExecutorService.get_executions_by_snapchat_account(
        db=db,
        snapchat_account_id=snapchat_account_id,
        limit=limit,
        offset=offset,
        execution_type=execution_type
    )
    return executions
