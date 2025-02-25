from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from typing import List, Optional
# from sqlalchemy.sql import func
from app.dtos.workflow_dtos import WorkflowCreateRequest, WorkflowResponse, WorkflowSimplifiedResponse, \
    WorkflowUpdateRequest, WorkflowSimplifiedNameResponse
from app.dtos.workflow_snapchat_account_response import WorkflowSnapchatAccountResponse
from app.models.workflow_status_enum import WorkflowStatusEnum
from app.schemas import SnapchatAccount
from app.schemas.workflow.workflow import Workflow
from app.schemas.workflow.workflow_step import WorkflowStep
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_


class WorkflowsService:

    @staticmethod
    def create_workflow(db: Session, agency_id:int, workflow_create: WorkflowCreateRequest) -> Workflow:
        # Create the workflow
        if not workflow_create.name or not isinstance(workflow_create.name, str):
            raise ValueError("Workflow name must be a non-empty string.")
        for step in workflow_create.steps:
            if not isinstance(step.day_offset, int) or step.day_offset < 0:
                raise ValueError(f"Invalid day_offset: {step.day_offset}. It must be a non-negative integer.")
            if not step.action_type:
                raise ValueError(f"Step action_type is missing or invalid: {step.action_type}.")
            if not isinstance(step.action_value, str):
                raise ValueError(f"Step action_value must be a string: {step.action_value}.")

        workflow = Workflow(name=workflow_create.name, description=workflow_create.description, status = workflow_create.status, agency_id = agency_id)
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        # Create the workflow steps
        for step_data in workflow_create.steps:
            workflow_step = WorkflowStep(
                workflow_id=workflow.id,
                day_offset=step_data.day_offset,
                action_type=step_data.action_type,
                action_value=step_data.action_value,
            )
            db.add(workflow_step)
        db.commit()

        # Refresh workflow to include steps in the response
        db.refresh(workflow)
        return workflow

    @staticmethod
    def list_workflows(db: Session, agency_id: int, name_filter: Optional[str] = None) -> List[Workflow]:
        query = db.query(Workflow).options(joinedload(Workflow.steps))
        query = query.filter(Workflow.agency_id == agency_id)
        if name_filter:
            query = query.filter(Workflow.name.ilike(f"%{name_filter}%"))
        workflows = query.all()
        return workflows

    @staticmethod
    def list_workflows_simplified(db: Session, agency_id: int) -> List[WorkflowSimplifiedNameResponse]:
        workflows = db.query(Workflow).filter(Workflow.agency_id == agency_id).all()
        return [
            WorkflowSimplifiedNameResponse(id=workflow.id, name=workflow.name)
            for workflow in workflows
        ]

    @staticmethod
    def get_workflow(db: Session, workflow_id: int) -> WorkflowResponse:
        workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )
        return WorkflowResponse.from_orm(workflow)

    @staticmethod
    def update_workflow(
            db: Session, workflow_id: int, workflow_update: WorkflowUpdateRequest
    ) -> Workflow:
        # Fetch the workflow
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )

        # Update workflow details
        if workflow_update.name:
            workflow.name = workflow_update.name
        if workflow_update.description:
            workflow.description = workflow_update.description

        # Prepare for syncing workflow steps
        existing_steps = {step.id: step for step in workflow.steps}  # Map of existing steps
        updated_step_ids = set()  # Track steps that are updated or added

        for step_data in workflow_update.steps:
            if step_data.id:  # Existing step
                if step_data.id in existing_steps:
                    step = existing_steps[step_data.id]
                    step.day_offset = step_data.day_offset
                    step.action_type = step_data.action_type
                    step.action_value = step_data.action_value
                    updated_step_ids.add(step.id)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Step ID {step_data.id} does not exist in workflow {workflow_id}.",
                    )
            else:  # New step
                new_step = WorkflowStep(
                    workflow_id=workflow_id,
                    day_offset=step_data.day_offset,
                    action_type=step_data.action_type,
                    action_value=step_data.action_value,
                )
                db.add(new_step)
                db.flush()  # Flush to generate ID for the new step
                updated_step_ids.add(new_step.id)

        # Delete steps that are no longer in the updated list
        for step in workflow.steps:
            if step.id not in updated_step_ids:
                db.delete(step)

        # Commit the changes
        db.commit()
        db.refresh(workflow)

        return workflow

    @staticmethod
    def delete_workflow(db: Session, workflow_id: int):
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )
        db.delete(workflow)
        db.commit()

    @staticmethod
    def restore_workflow(db: Session, workflow_id: int) -> WorkflowResponse:
        workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )
        # Logic for restoration (if applicable)
        # For example, updating a "deleted" field or similar
        db.commit()
        return WorkflowResponse.from_orm(workflow)

    @staticmethod
    def update_workflow_status(db: Session, workflow_id: int, new_status: WorkflowStatusEnum) -> Workflow:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )

        # Update the workflow status
        workflow.status = new_status
        db.commit()
        db.refresh(workflow)
        return workflow

    @staticmethod
    def get_snapchat_accounts_with_last_executed_step(db: Session, workflow_id: int) -> List[WorkflowSnapchatAccountResponse]:
        """
        Retrieves all Snapchat accounts for a given workflow and their last executed workflow step.
        """
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")

        current_date = datetime.utcnow()

        days_since_creation = (
                func.extract('epoch', func.now() - SnapchatAccount.added_to_system_date) / 86400
        )

        # Build the query
        query = (
            db.query(
                SnapchatAccount,
                func.coalesce(func.max(WorkflowStep.day_offset), -1).label("last_executed_step")
            )
            .join(Workflow, Workflow.id == SnapchatAccount.workflow_id)
            # Outer join with a custom condition: step.day_offset <= days_since_creation
            .outerjoin(
                WorkflowStep,
                and_(
                    WorkflowStep.workflow_id == Workflow.id,
                    days_since_creation >= WorkflowStep.day_offset  # Only include steps up to current account's age
                )
            )
            .filter(Workflow.id == workflow_id)
            .group_by(SnapchatAccount.id)
            .order_by(SnapchatAccount.id)  # Optional ordering
        )

        accounts_with_steps = query.all()

        # Transform data into DTOs
        return [
            WorkflowSnapchatAccountResponse(
                snapchat_account=account,
                last_executed_step=step if step else None
            )
            for account, step in accounts_with_steps
        ]
