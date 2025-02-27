import logging
from celery import Celery
from sqlalchemy.orm import joinedload
from datetime import datetime
from croniter.croniter import step_search_re
from app.celery_app import celery
from app.database import SessionLocal
from app.models.workflow_step_type_enum import WorkflowStepTypeEnum
from app.schemas import SnapchatAccount
from app.schemas.workflow.workflow import Workflow
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

class WorkflowTaskManager:
    @staticmethod
    @celery.task
    def execute_workflows():
        """
        Executes workflows and applies the steps to associated Snapchat accounts
        based on their creation date and the workflow configuration.
        """
        try:
            with SessionLocal() as db:
                workflows = []  # Ensure workflows is always defined
                try:
                    # Fetch all workflows and their steps in a single query
                    workflows = (
                        db.query(Workflow)
                        .options(joinedload(Workflow.steps))  # Eagerly load steps for efficiency
                        .all()
                    )
                except Exception as e:
                    logger.error(f"[WORKFLOW_EXECUTION_JOB]* Failed to fetch workflows: {e}")
                    return  # Exit early if workflows cannot be loaded

                for workflow in workflows:
                    try:
                        logger.info(f"[WORKFLOW_EXECUTION_JOB]* Processing workflow: {workflow.name} (ID: {workflow.id})")
                        if not SubscriptionService.is_subscription_available(db, workflow.agency_id):
                            logger.info(
                                f"[WORKFLOW_EXECUTION_JOB]* Workflow: {workflow.name} (ID: {workflow.id}) was not executed because subscription is expired")
                            continue
                        # Fetch accounts associated with the workflow
                        snapchat_accounts = []
                        try:
                            snapchat_accounts = (
                                db.query(SnapchatAccount)
                                .filter(SnapchatAccount.workflow_id == workflow.id)
                                .all()
                            )
                        except Exception as e:
                            logger.error(f"[WORKFLOW_EXECUTION_JOB]* Failed to fetch accounts for workflow {workflow.id}: {e}")
                            continue  # Skip to the next workflow if accounts cannot be loaded

                        for snapchat_account in snapchat_accounts:
                            try:
                                # Calculate the days since the account's creation
                                days_since_creation = (datetime.now() - snapchat_account.added_to_system_date).days

                                # Filter steps that should be executed today
                                steps_to_be_executed_today = [
                                    step for step in workflow.steps if step.day_offset == days_since_creation
                                ]

                                for step in steps_to_be_executed_today:
                                    try:
                                        # Handle step actions
                                        if step.action_type == WorkflowStepTypeEnum.CHANGE_STATUS:
                                            snapchat_account.status = step.action_value  # Assign directly
                                        elif step.action_type == WorkflowStepTypeEnum.ADD_TAG:
                                            if snapchat_account.tags is None:
                                                snapchat_account.tags = []
                                            if step.action_value not in snapchat_account.tags:
                                                snapchat_account.tags.append(step.action_value)  # Ensure no duplicates
                                                snapchat_account.tags = list(snapchat_account.tags)
                                        elif step.action_type == WorkflowStepTypeEnum.REMOVE_TAG:
                                            if snapchat_account.tags is None:
                                                snapchat_account.tags = []
                                            if step.action_value in snapchat_account.tags:
                                                snapchat_account.tags.remove(step.action_value)
                                                snapchat_account.tags = list(snapchat_account.tags)
                                    except Exception as e:
                                        logger.error(
                                            f"[WORKFLOW_EXECUTION_JOB]* Error processing step {step.id} for account {snapchat_account.id}: {e}"
                                        )
                                        continue  # Skip this step and continue with others
                                db.add(snapchat_account)
                            except Exception as e:
                                logger.error(f"[WORKFLOW_EXECUTION_JOB]* Error processing account {snapchat_account.id}: {e}")
                                continue  # Skip this account and proceed to others

                        # Commit changes for this workflow
                        try:
                            db.commit()
                            logger.info(f"[WORKFLOW_EXECUTION_JOB]* Successfully processed workflow: {workflow.name} (ID: {workflow.id})")
                        except Exception as e:
                            logger.error(f"[WORKFLOW_EXECUTION_JOB]* Failed to commit changes for workflow {workflow.id}: {e}")
                            db.rollback()  # Rollback only changes for this workflow
                    except Exception as e:
                        logger.error(f"[WORKFLOW_EXECUTION_JOB]* Critical error in workflow {workflow.id}: {e}")
                        continue  # Skip to the next workflow

        except Exception as e:
            logger.critical(f"[WORKFLOW_EXECUTION_JOB]* Critical failure in execute_workflows: {e}")