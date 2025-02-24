import logging

from app.celery_app import celery
from app.database import SessionLocal
from app.models.execution_type_enum import ExecutionTypeEnum
from app.schemas.executions.execution import Execution
from app.schemas.executions.account_execution import AccountExecution  # Ensure the model is imported
from app.schemas.snapchat_account import SnapchatAccount
from app.models.status_enum import StatusEnum
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from app.services.job_executor_service import JobExecutorService
from datetime import datetime
from celery import group, chord
from typing import Optional
from sqlalchemy.orm import Session
from app.event_listeners import log_status_change
from app.services.snapchat_account_statistics_service import SnapchatAccountStatisticsService

logger = logging.getLogger(__name__)

class ExecutionTaskManager:
    @staticmethod
    @celery.task
    def execute_task_celery(execution_id: int, account_ids: Optional[list]):
        """
        Execute the main task, creating ExecutionAccount objects, launching child tasks in parallel.
        Waits for all child tasks to complete and updates the main execution status.
        """
        # connect_debugger()
        logger.info(f"[CELERY] Execution {execution_id} started.")
        db = SessionLocal()
        # Fetch the Execution record
        result = db.execute(select(Execution).filter(Execution.id == execution_id))

        execution = result.scalars().first()
        try:

            if not execution:
                logger.info(f"Execution {execution_id} not found!")
                return {"message": f"Execution {execution_id} not found."}

            # Set execution status to IN_PROGRESS
            execution.status = StatusEnum.IN_PROGRESS
            db.commit()

            # Create ExecutionAccount objects
            account_executions = []
            if execution.type == ExecutionTypeEnum.GENERATE_LEADS:
                snapchat_accounts = SnapchatAccountStatisticsService.select_top_n_snapchat_accounts_optimized(
                    session=db,
                    n=execution.configuration["accounts_number"],
                    weight_rejecting_rate=execution.configuration["weight_rejecting_rate"],
                    weight_conversation_rate=execution.configuration["weight_conversation_rate"],
                    weight_conversion_rate=execution.configuration["weight_conversion_rate"]
                )
                account_ids = [snapchat_account.id for snapchat_account in snapchat_accounts]
                if account_ids:
                    execution.configuration["leads_per_account"] = (
                            execution.configuration["target_lead_number"] / len(account_ids)
                    )
                else:
                    execution.configuration["leads_per_account"] = 0
                db.add(execution)

            if execution.type == ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS and not account_ids:
                snapchat_accounts = SnapchatAccountStatisticsService.get_accounts_by_thresholds(
                    session=db,
                    max_rejecting_rate_threshold=execution.configuration["max_rejection_rate"],
                    min_conversation_rate_threshold=execution.configuration["min_conversation_rate"],
                    min_conversion_rate_threshold=execution.configuration["min_conversion_rate"],
                )
                account_ids = list(set(snapchat_account.id for snapchat_account in snapchat_accounts))

            for account_id in account_ids:
                execution_account = AccountExecution(
                    execution_id=execution_id,
                    snap_account_id=account_id,
                    status=StatusEnum.STARTED,
                    type=execution.type
                )
                db.add(execution_account)
                account_executions.append(execution_account)
            db.commit()

            child_tasks = []
            for ae, acc_id in zip(account_executions, account_ids):
                child_tasks.append(
                    ExecutionTaskManager.execute_child_task_celery.s(ae.id, acc_id)
                )

            chord_job = chord(group(child_tasks))(
                ExecutionTaskManager.finalize_execution.s(execution_id)
            )

            return {
                "message": f"Chord created for execution {execution_id}",
                "chord_id": chord_job.id
            }

        except Exception as e:
            logger.error(f"[CELERY] Error during execution {execution_id}: {e}")
            if execution:
                execution.status = StatusEnum.FAILURE
                execution.end_time = datetime.utcnow()
                db.commit()
        finally:
            db.close()

        return {"message": f"Execution {execution_id} queued child tasks."}

    @staticmethod
    @celery.task
    def execute_child_task_celery(execution_account_id, account_id):
        # connect_debugger()
        db = SessionLocal()
        try:
            # 1) Do the child processing
            account_execution = JobExecutorService.get_execution_account(db, execution_account_id)

            if not account_execution:
                logger.info(f"ExecutionAccount {execution_account_id} not found!")
                return {"status": StatusEnum.FAILURE.value, "execution_account_id": execution_account_id}

            snap_account_id = account_execution.snap_account_id
            other_executions = JobExecutorService.get_other_executions(db, snap_account_id)

            if other_executions:
                account_execution.status = StatusEnum.EXECUTION_ALREADY_IN_PROGRESS
                account_execution.message = f"Found another execution that is in progress, execution id: {other_executions.id}"
                db.commit()
                return {"status": account_execution.status.value, "execution_account_id": execution_account_id}

            execution = account_execution.execution
            if not execution:
                account_execution.status = StatusEnum.FAILURE
                logger.info(f"Associated Execution for ExecutionAccount {execution_account_id} not found!")
                return {"status": account_execution.status.value, "execution_account_id": execution_account_id}

            # Update status to IN_PROGRESS
            account_execution.status = StatusEnum.IN_PROGRESS
            db.commit()

            # Fetch the Snapchat account
            query = select(SnapchatAccount).where(SnapchatAccount.id == account_id)
            if execution.type != ExecutionTypeEnum.COMPUTE_STATISTICS:
                query = query.options(
                    selectinload(SnapchatAccount.proxy),
                    selectinload(SnapchatAccount.device),
                    selectinload(SnapchatAccount.cookies),
                    selectinload(SnapchatAccount.snapchat_account_login)
                )
            else:
                query = query.options(
                    selectinload(SnapchatAccount.stats),
                    selectinload(SnapchatAccount.snapchat_account_login)
                )
            snapchat_account = db.execute(query).scalars().first()

            if not snapchat_account:
                logger.info(f"Snapchat Account {account_id} not found!")
                account_execution.status = StatusEnum.FAILURE
                account_execution.message = f"Snapchat Account with id {account_id} not found"
                db.commit()
                return {"status": account_execution.status.value}

            execution_type = account_execution.execution.type

            if execution_type == ExecutionTypeEnum.QUICK_ADDS or execution_type == ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS:
                JobExecutorService.handle_quick_adds(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.CHECK_CONVERSATIONS:
                JobExecutorService.handle_check_conversations(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.SEND_TO_USER:
                JobExecutorService.handle_send_to_user(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.STATUS_CHECK:
                JobExecutorService.handle_check_status(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.COMPUTE_STATISTICS:
                JobExecutorService.handle_compute_statistics(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.GENERATE_LEADS:
                JobExecutorService.handle_generate_leads(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.CONSUME_LEADS:
                JobExecutorService.handle_consume_leads(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.SET_BITMOJI:
                JobExecutorService.handle_set_bitmoji(db, account_execution, snapchat_account)
            elif execution_type == ExecutionTypeEnum.CHANGE_BITMOJI:
                JobExecutorService.handle_change_bitmoji(db, account_execution, snapchat_account)
            else:
                message = f"Unsupported execution type: {execution_type}"
                print(message)
                account_execution.status = StatusEnum.FAILURE
                account_execution.message = message

            account_execution.end_time = datetime.utcnow()
            db.commit()

            return {"status": account_execution.status.value, "execution_account_id": execution_account_id}

        except Exception as e:
            # handle error
            return {"status": "FAILURE", "error": str(e), "execution_account_id": execution_account_id}
        finally:
            db.close()

    @staticmethod
    @celery.task
    def finalize_execution(child_results, execution_id):
        """
        This callback runs after ALL child tasks in the chord have completed.
        'child_results' is a list of return values from each child task.
        """
        db: Session = SessionLocal()
        logger.info(f"Finalizing execution with ID {execution_id}.")
        try:
            execution = db.query(Execution).filter_by(id=execution_id).first()
            if not execution:
                logger.error(f"Execution with ID {execution_id} not found.")
                return {"error": f"Execution with ID {execution_id} not found."}

            has_failure = False
            for child_result in child_results:
                status = child_result.get("status")
                error = child_result.get("error")
                execution_account_id = child_result.get("execution_account_id")
                if status == "FAILURE" and error:
                    has_failure = True
                    account_execution = JobExecutorService.get_execution_account(
                        db, child_result.get("execution_account_id")
                    )
                    if account_execution:
                        account_execution.status = StatusEnum.FAILURE
                        account_execution.message = child_result.get("error", "Unknown error")
                    else:
                        logging.warning(f"Execution account {child_result.get('execution_account_id')} not found.")

            execution.status = StatusEnum.FAILURE if has_failure else StatusEnum.DONE
            execution.end_time = datetime.utcnow()
            db.commit()

            execution_data = {
                "execution_id": execution_id,
                "final_status": execution.status.name,
                "end_time": execution.end_time.isoformat()
            }
            return execution_data
        except Exception as e:
            db.rollback()
            logger.error(f"Error finalizing execution {execution_id}: {str(e)}")
            return {"error": f"Failed to finalize execution {execution_id}. Error: {str(e)}"}
        finally:
            db.close()