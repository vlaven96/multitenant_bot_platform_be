from typing import Optional, List, Any, Dict
from sqlalchemy.orm import aliased
from sqlalchemy import select, func
from app.dtos.execution_create_request import ExecutionCreateRequest
from app.dtos.execution_result_response import ExecutionResultResponse
from app.dtos.execution_simple_response import ExecutionSimpleResponse
from app.models.account_status_enum import AccountStatusEnum
from app.models.operation_models.consume_leads_config import ConsumeLeadsConfig
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.operation_models.quick_ads_config import QuickAdsConfig
from app.models.status_enum import StatusEnum
from app.schemas.executions.execution import Execution
from app.schemas.executions.account_execution import AccountExecution  # Ensure the model is imported
from app.schemas.executions.job import Job
from app.schemas.snapchat_account import SnapchatAccount
from app.services.snapchat_account_statistics_service import SnapchatAccountStatisticsService
from app.services.snapchat_service import SnapchatService
from fastapi import HTTPException
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm import Session

from app.utils.error_message_status_dict import STATUS_MAPPING_ACCOUNTS, STATUS_MAPPING_EXECUTIONS
from app.utils.user_frinedly_message_utils import UserFriendlyMessageUtils


class JobExecutorService:
    REQUIRED_QUICK_ADDS_CONFIG_KEYS = {"requests", "batches", "batch_delay", "max_quick_add_pages",
                                       "argo_tokens", "users_sent_in_request"}
    REQUIRED_QUICK_ADDS_TOP_ACCOUNTS_CONFIG_KEYS = {"requests", "batches", "batch_delay", "max_quick_add_pages",
                                       "argo_tokens", "users_sent_in_request", "max_rejection_rate", "min_conversation_rate", "min_conversation_rate"}
    # REQUIRED_CHECK_FRIENDS_CONFIG_KEYS = {"starting_delay"}
    REQUIRED_SENT_TO_USERS_CONFIG_KEYS = {"username"}
    REQUIRED_GENERATED_LEADS_CONFIG_KEYS = {"accounts_number", "target_lead_number", "weight_rejecting_rate", "weight_conversation_rate", "weight_conversion_rate"}
    REQUIRED_CONSUME_LEADS_CONFIG_KEYS = {"requests", "batches", "batch_delay",
                                       "argo_tokens", "users_sent_in_request"}

    @staticmethod
    def provide_default_config2(type, configuration: Dict[str, Any]):

        # Set starting_delay for all types by default
        configuration['starting_delay'] = 300

        if type == ExecutionTypeEnum.QUICK_ADDS:
            configuration['max_quick_add_pages'] = 10
            configuration['users_sent_in_request'] = 10
            configuration['argo_tokens'] = False
            configuration['batches'] = 1
            configuration['batch_delay'] = 10

    @staticmethod
    def provide_default_config(execution_request: ExecutionCreateRequest):
        # Calculate the number of accounts using the length of the list if it exists
        accounts_num = len(execution_request.accounts) if execution_request.accounts else 1
        delay_seconds = (accounts_num - 1) * 3

        # Set starting_delay for all types by default
        execution_request.configuration['starting_delay'] = delay_seconds

        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.QUICK_ADDS:
            execution_request.configuration['max_quick_add_pages'] = 10
            execution_request.configuration['users_sent_in_request'] = 10
            execution_request.configuration['argo_tokens'] = False
            execution_request.configuration['batches'] = 1
            execution_request.configuration['batch_delay'] = 10


    @staticmethod
    def validate_executor(execution_request: ExecutionCreateRequest):
        """
        Validates the execution request.
        Raises HTTPException if the request is invalid.

        :param execution_request: The request object to validate.
        """
        # Validate execution type
        if execution_request.type not in ExecutionTypeEnum.__members__.keys():
            allowed_types = ", ".join(ExecutionTypeEnum.__members__.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type '{execution_request.type}'. Allowed types are: {allowed_types}."
            )

        # Ensure accounts are provided
        if ExecutionTypeEnum(execution_request.type) != ExecutionTypeEnum.GENERATE_LEADS and ExecutionTypeEnum(execution_request.type) != ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS and not execution_request.accounts:
            raise HTTPException(
                status_code=400,
                detail="At least one account ID should be present in 'accounts'."
            )

        # Additional validation for QUICK_ADDS type
        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.QUICK_ADDS:
            missing_keys = JobExecutorService.REQUIRED_QUICK_ADDS_CONFIG_KEYS - execution_request.configuration.keys()
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid request for type '{execution_request.type}'. "
                        f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
                        f"Required keys: {', '.join(JobExecutorService.REQUIRED_QUICK_ADDS_CONFIG_KEYS)}."
                    )
                )
        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS:
            missing_keys = JobExecutorService.REQUIRED_QUICK_ADDS_TOP_ACCOUNTS_CONFIG_KEYS - execution_request.configuration.keys()
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid request for type '{execution_request.type}'. "
                        f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
                        f"Required keys: {', '.join(JobExecutorService.REQUIRED_QUICK_ADDS_TOP_ACCOUNTS_CONFIG_KEYS)}."
                    )
                )
        # if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.CHECK_CONVERSATIONS:
        #     missing_keys = JobExecutorService.REQUIRED_CHECK_FRIENDS_CONFIG_KEYS - execution_request.configuration.keys()
        #     if missing_keys:
        #         raise HTTPException(
        #             status_code=400,
        #             detail=(
        #                 f"Invalid request for type '{execution_request.type}'. "
        #                 f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
        #                 f"Required keys: {', '.join(JobExecutorService.REQUIRED_CHECK_FRIENDS_CONFIG_KEYS)}."
        #             )
        #         )
        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.SEND_TO_USER:
            missing_keys = JobExecutorService.REQUIRED_SENT_TO_USERS_CONFIG_KEYS - execution_request.configuration.keys()
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid request for type '{execution_request.type}'. "
                        f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
                        f"Required keys: {', '.join(JobExecutorService.REQUIRED_SENT_TO_USERS_CONFIG_KEYS)}."
                    )
                )

        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.GENERATE_LEADS:
            missing_keys = JobExecutorService.REQUIRED_GENERATED_LEADS_CONFIG_KEYS - execution_request.configuration.keys()
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid request for type '{execution_request.type}'. "
                        f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
                        f"Required keys: {', '.join(JobExecutorService.REQUIRED_SENT_TO_USERS_CONFIG_KEYS)}."
                    )
                )
        if ExecutionTypeEnum(execution_request.type) == ExecutionTypeEnum.CONSUME_LEADS:
            missing_keys = JobExecutorService.REQUIRED_CONSUME_LEADS_CONFIG_KEYS - execution_request.configuration.keys()
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid request for type '{execution_request.type}'. "
                        f"Configuration is missing the following keys: {', '.join(missing_keys)}. "
                        f"Required keys: {', '.join(JobExecutorService.REQUIRED_SENT_TO_USERS_CONFIG_KEYS)}."
                    )
                )

    @staticmethod
    def get_executionsV3(
            db: Session,
            agency_id:int,
            limit: int = 20,
            offset: int = 0,
            username: Optional[str] = None,
            status: Optional[StatusEnum] = None,
            execution_type: Optional[ExecutionTypeEnum] = None,
            job_id: Optional[int] = None
    ) -> List[ExecutionResultResponse]:
        """
        Retrieve paginated Executions, with optional filtering by username and status.
        Then fetch aggregated counts of AccountExecution status for each Execution.
        Return a list of ExecutionResultResponse.
        """

        subq = db.query(Execution.id, Execution.start_time)
        subq = subq.filter(Execution.agency_id == agency_id)
        # If filtering, join with AccountExecution (and possibly SnapchatAccount)
        if username or status or execution_type or job_id:
            subq = subq.join(Execution.account_executions)
            if execution_type:
                subq = subq.filter(Execution.type == execution_type.value)
            if job_id:
                subq = subq.filter(Execution.job_id == job_id)
            if username:
                subq = subq.join(AccountExecution.snapchat_account)
                subq = subq.filter(SnapchatAccount.username.ilike(f"%{username}%"))
            if status:
                subq = subq.filter(AccountExecution.status == status.value)

        # Use distinct so that each (id, start_time) appears only once
        subq = subq.distinct()

        # Order by start_time desc, then offset/limit
        subq = subq.order_by(Execution.start_time.desc())
        subq = subq.offset(offset).limit(limit)

        # Grab the IDs from the subquery
        rows = subq.all()  # each row is (id, start_time)
        execution_ids = [r.id for r in rows]

        # If no Execution IDs, return empty
        if not execution_ids:
            return []

        # --- Query 2: Get full Execution + aggregated status counts for those IDs ---
        results = (
            db.query(
                Execution,
                AccountExecution.status,
                Job.name,
                func.count(AccountExecution.status).label("status_count")
            )
                .outerjoin(Execution.account_executions)
                .outerjoin(Execution.job)
                .filter(Execution.id.in_(execution_ids))
                .group_by(Execution.id, AccountExecution.status, Job.name)
                .order_by(Execution.start_time.desc())
                .all()
        )

        # --- Transform the results into the desired structure ---
        structured_results = {}
        for execution, account_status, job_name, status_count in results:
            if execution not in structured_results:
                structured_results[execution] = {"execution": execution, "results": {}, "job_name": job_name}

            # If there's no status (e.g., None), give it a "unknown" key
            account_status_key = account_status.value if account_status else "unknown"
            structured_results[execution]["results"][account_status_key] = status_count

        # --- Build the final Pydantic responses ---
        serialized_results: List[ExecutionResultResponse] = []
        for execution, data in structured_results.items():
            execution_response = ExecutionSimpleResponse.from_orm(execution)
            results_data = data["results"] if data["results"] else None
            serialized_results.append(
                ExecutionResultResponse(execution=execution_response, results=results_data, job_name = data["job_name"])
            )

        return serialized_results

    @staticmethod
    def get_execution_account(db, execution_account_id):
        result = db.execute(
            select(AccountExecution)
                .options(selectinload(AccountExecution.execution))  # Eagerly load the execution relationship
                .filter(AccountExecution.id == execution_account_id)
        )
        account_execution = result.scalars().first()

        if not account_execution:
            print(f"ExecutionAccount {execution_account_id} not found!")
        return account_execution

    @staticmethod
    def get_other_executions(db, snap_account_id):
        result = db.execute(
            select(AccountExecution)
                .where(
                AccountExecution.snap_account_id == snap_account_id,
                AccountExecution.status == StatusEnum.IN_PROGRESS.value
            )
        )
        return result.scalars().first()

    @staticmethod
    def handle_quick_adds(db, account_execution, snapchat_account):
        # Fetch the Snapchat account
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)
        quick_ads_config = QuickAdsConfig(
            account_execution_id=account_execution.id,
            max_starting_delay=configuration.get("starting_delay", 60),
            requests=configuration["requests"],
            batches=configuration["batches"],
            batch_delay=configuration["batch_delay"],
            max_quick_add_pages=configuration["max_quick_add_pages"],
            users_sent_in_request=configuration["users_sent_in_request"],
            argo_tokens=configuration["argo_tokens"]
        )
        quick_add_result = snapchat_service.process_quick_adds_batch(
            snapchat_account,
            quick_ads_config)


        account_execution.status = StatusEnum.DONE if quick_add_result.success else StatusEnum.FAILURE
        account_execution.message = quick_add_result.message
        account_execution.result = {
            "total_sent_requests": quick_add_result.total_sent_requests,
            "total_rejected_count": quick_add_result.rejected_count,
            "total_quick_add_pages_requested": quick_add_result.quick_add_pages_requested,
            "added_users": quick_add_result.added_users,
        }

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, quick_add_result
        )

    @staticmethod
    def handle_check_conversations(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)

        check_conversations_result = snapchat_service.process_get_conversations(
            snapchat_account,
            account_execution.id,
            configuration.get("starting_delay", 60)
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, check_conversations_result
        )

    @staticmethod
    def handle_send_to_user(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)

        check_conversations_result = snapchat_service.process_send_to_user(
            snapchat_account,
            account_execution.id,
            configuration.get("starting_delay", 60),
            configuration.get("username")
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, check_conversations_result
        )

    @staticmethod
    def handle_check_status(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)

        check_status_result = snapchat_service.process_check_status(
            snapchat_account,
            account_execution.id,
            configuration.get("starting_delay", 60),
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, check_status_result
        )

    @staticmethod
    def handle_compute_statistics(db, account_execution, snapchat_account):
        check_status_result = SnapchatAccountStatisticsService.compute_statistics(
            db,
            snapchat_account,
            account_execution.id,
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, check_status_result
        )

    @staticmethod
    def handle_generate_leads(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)
        generate_leads_result = snapchat_service.generate_leads(
            snapchat_account,
            account_execution.id,
            configuration.get("leads_per_account", 10),
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, generate_leads_result
        )

    @staticmethod
    def handle_consume_leads(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)
        consume_leads_config = ConsumeLeadsConfig(
            account_execution_id=account_execution.id,
            max_starting_delay=configuration.get("starting_delay", 0),
            requests=configuration["requests"],
            batches=configuration["batches"],
            batch_delay=configuration["batch_delay"],
            users_sent_in_request=configuration["users_sent_in_request"],
            argo_tokens=configuration["argo_tokens"]
        )
        process_leads_result = snapchat_service.process_consume_leads_batch(
            snapchat_account,
            consume_leads_config
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, process_leads_result
        )

    @staticmethod
    def handle_set_bitmoji(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)

        set_bitmoji_result = snapchat_service.process_set_bitmoji(
            snapchat_account,
            configuration.get("starting_delay", 0),
            account_execution.id
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, set_bitmoji_result
        )

    @staticmethod
    def handle_change_bitmoji(db, account_execution, snapchat_account):
        configuration = account_execution.execution.configuration
        snapchat_service = SnapchatService(db)

        set_bitmoji_result = snapchat_service.process_change_bitmoji(
            snapchat_account,
            configuration.get("starting_delay", 0),
            account_execution.id
        )

        JobExecutorService.update_execution_account_with_result(
            db, account_execution, snapchat_account, set_bitmoji_result
        )

    @staticmethod
    def update_execution_account_with_result(db, account_execution, snapchat_account, result):
        account_execution.status = StatusEnum.DONE if result.success else StatusEnum.FAILURE
        account_execution.message = result.message
        account_execution.result = result.__dict__

        if result.success:
            for keyword, status in STATUS_MAPPING_EXECUTIONS.items():
                if keyword in result.message:
                    account_execution.status = status
                    break
            if snapchat_account.status != AccountStatusEnum.CAPTCHA:
                snapchat_account.status = AccountStatusEnum.GOOD_STANDING
        else:
            for keyword, status in STATUS_MAPPING_ACCOUNTS.items():
                if keyword in result.message:
                    snapchat_account.status = status
                    break
            for keyword, status in STATUS_MAPPING_EXECUTIONS.items():
                if keyword in result.message:
                    account_execution.status = status
                    break


        # Clear proxy ID if the account is in a critical status
        if snapchat_account.status in (
                AccountStatusEnum.COMPROMISED_LOCKED,
                AccountStatusEnum.INCORRECT_PASSWORD,
                AccountStatusEnum.LOCKED
        ):
            snapchat_account.proxy_id = None
        if snapchat_account.status == AccountStatusEnum.TEMPORARY_LOCKED:
            snapchat_account.workflow_id = None
        db.commit()

    @staticmethod
    def get_execution_by_id(
            db: Session,
            execution_id: int
    ) -> Optional[Execution]:
        """
        Retrieve a specific execution by its ID along with associated objects.
        """
        execution = (
            db.query(Execution)
                .options(joinedload(Execution.account_executions).joinedload(AccountExecution.snapchat_account))
                .filter(Execution.id == execution_id)
                .first()
        )
        if not execution:
            raise ValueError(f"Execution with ID {execution_id} does not exist.")

        for account_execution in execution.account_executions:
            if(account_execution.status == StatusEnum.SNAPKAT_API_RATE_LIMIT_EXCEEDED):
                account_execution.status = StatusEnum.FAILURE
            if account_execution.message:
                account_execution.message = UserFriendlyMessageUtils.get_user_friendly_message(account_execution.message)

        return execution

    def get_executions_by_snapchat_account(
            db: Session, snapchat_account_id: int,
            limit: int,
            offset: int,
            execution_type: Optional[ExecutionTypeEnum] = None
    ) -> List[Execution]:
        """
        Retrieve all Execution records that have at least one AccountExecution
        for the specified snapchat_account_id. Eager-load the account_executions
        and their related snapchat_account, but keep only the relevant child rows.
        """

        # Alias for filtering related account executions
        AE = aliased(AccountExecution)

        # Subquery: fetch the execution_ids which have an AccountExecution referencing snapchat_account_id
        subq = (
            db.query(AE.execution_id)
                .filter(AE.snap_account_id == snapchat_account_id)
        )

        # Add optional execution_type filter to the subquery
        if execution_type:
            subq = subq.join(Execution).filter(Execution.type == execution_type.value)

        subq = subq.subquery()

        # Main query: retrieve Execution rows whose IDs are in the subquery
        executions = (
            db.query(Execution)
                .filter(Execution.id.in_(subq))
                # Eager-load the related account_executions and their snapchat_account
                .options(
                selectinload(Execution.account_executions)
                    .selectinload(AccountExecution.snapchat_account)
            )
                .order_by(Execution.start_time.desc())
                .offset(offset)
                .limit(limit)
                .all()
        )

        # In-memory filter: keep only the account_executions that match the snapchat_account_id
        for execution in executions:
            execution.account_executions = [
                ae for ae in execution.account_executions
                if ae.snap_account_id == snapchat_account_id
            ]

        return executions
