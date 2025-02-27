from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, asc, or_
from sqlalchemy.exc import IntegrityError
from collections import defaultdict

from app.dtos.account_execution_simple_response import AccountExecutionSimpleResponse
from app.dtos.model_response import ModelResponse
from app.dtos.proxy_response import ProxyResponse
from app.dtos.chatbot_response import ChatBotResponse
from app.dtos.proxy_simple_response import ProxySimpleResponse
from app.dtos.snapchat_account_response import SnapchatAccountResponseV2
from app.dtos.snapchat_account_edit_response import SnapchatAccountEditResponse
from app.dtos.workflow_dtos import WorkflowSimplifiedNameResponse
from app.models.account_status_enum import AccountStatusEnum
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.status_enum import StatusEnum
from app.models.workflow_step_type_enum import WorkflowStepTypeEnum
from app.schemas import SnapchatAccountStats
from app.schemas.chatbot import ChatBot
from app.schemas.cookies import Cookies
from app.schemas.executions.account_execution import AccountExecution
from app.schemas.executions.execution import Execution
from app.schemas.model import Model
from app.schemas.proxy import Proxy
from app.schemas.snapchat_account import SnapchatAccount
from app.schemas.workflow.workflow import Workflow
from app.schemas.workflow.workflow_step import WorkflowStep
from app.utils.snapchat_account_utils import SnapchatAccountUtils
from sqlalchemy.orm import joinedload
from sqlalchemy import select, distinct, exists, and_
import re

class SnapchatAccountService:
    @staticmethod
    def get_all_accounts(
            db: Session,
            username: Optional[str] = None,
            creation_date_from: Optional[datetime] = None,
            creation_date_to: Optional[datetime] = None,
            has_proxy: Optional[bool] = None,
            has_device: Optional[bool] = None,
            has_cookies: Optional[bool] = None,
            statuses: Optional[List[AccountStatusEnum]] = None
    ) -> List[SnapchatAccount]:
        """
        Retrieves all Snapchat accounts with optional filters.
        """
        query = db.query(SnapchatAccount).options(
            joinedload(SnapchatAccount.model),
            joinedload(SnapchatAccount.chat_bot)
        )
        if username:
            query = query.filter(SnapchatAccount.username.ilike(f"%{username}%"))

        if creation_date_from:
            query = query.filter(SnapchatAccount.creation_date >= creation_date_from)

        if creation_date_to:
            query = query.filter(SnapchatAccount.creation_date <= creation_date_to)

        if has_proxy is not None:
            query = query.filter(SnapchatAccount.proxy != None if has_proxy else SnapchatAccount.proxy == None)

        if has_device is not None:
            query = query.filter(SnapchatAccount.device != None if has_device else SnapchatAccount.device == None)

        if has_cookies is not None:
            query = query.filter(SnapchatAccount.cookies != None if has_cookies else SnapchatAccount.cookies == None)

        if statuses:
            query = query.filter(SnapchatAccount.status.in_(statuses))

        snapchat_accounts = query.all()
        for snapchat_account in snapchat_accounts:
            if snapchat_account.account_executions:
                snapchat_account.account_executions = sorted(
                    snapchat_account.account_executions,
                    key=lambda x: x.start_time,
                    reverse=True
                )[:3]

        return snapchat_accounts

    @staticmethod
    def get_all_accountsV2(
            db: Session,
            agency_id: int,
            username: Optional[str] = None,
            creation_date_from: Optional[datetime] = None,
            creation_date_to: Optional[datetime] = None,
            has_proxy: Optional[bool] = None,
            has_device: Optional[bool] = None,
            has_cookies: Optional[bool] = None,
            statuses: Optional[List[AccountStatusEnum]] = None,
            # New parameters:
            page: Optional[int] = None,
            page_size: Optional[int] = None,
            include_executions: bool = False,
            has_quick_adds: bool = False  #
    ) -> List[SnapchatAccount]:
        """
        Retrieves all Snapchat accounts with optional filters.
        - If 'include_executions' is True, also load 'account_executions'
          and slice the top 3 sorted by 'start_time' descending.
        - If 'page' and 'page_size' are provided, apply pagination.
        """

        # Base query with joinedload for model & chat_bot
        # If we want to include executions, use selectinload for them (one extra query, no N+1)
        load_options = [
            joinedload(SnapchatAccount.model),
            joinedload(SnapchatAccount.chat_bot),
            joinedload(SnapchatAccount.device),
            joinedload(SnapchatAccount.cookies),
            joinedload(SnapchatAccount.proxy),
            joinedload(SnapchatAccount.workflow)
        ]

        query = db.query(SnapchatAccount).options(*load_options)
        query = query.filter(SnapchatAccount.agency_id == agency_id)
        # --- Apply Filters ---
        if username:
            query = query.filter(SnapchatAccount.username.ilike(f"%{username}%"))
        if creation_date_from:
            query = query.filter(SnapchatAccount.creation_date >= creation_date_from)
        if creation_date_to:
            query = query.filter(SnapchatAccount.creation_date <= creation_date_to)
        if has_proxy is not None:
            query = query.filter(
                SnapchatAccount.proxy != None if has_proxy else SnapchatAccount.proxy == None
            )
        if has_device is not None:
            query = query.filter(
                SnapchatAccount.device != None if has_device else SnapchatAccount.device == None
            )
        if has_cookies is not None:
            query = query.filter(
                SnapchatAccount.cookies != None if has_cookies else SnapchatAccount.cookies == None
            )
        query = query.filter(SnapchatAccount.status != AccountStatusEnum.TERMINATED)
        if statuses:
            query = query.filter(SnapchatAccount.status.in_(statuses))
        if has_quick_adds:
            # Condition 1: There is an associated stats record with quick_ads_sent > 40.
            stats_condition = exists().where(
                and_(
                    SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id,
                    SnapchatAccountStats.quick_ads_sent >= 20,
                )
            )

            # Condition 2: There is NO stats record...
            no_stats_condition = ~exists().where(
                SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id
            )

            # ...and in that case, there must be at least 2 executions of type QUICK_ADDS with status DONE.
            execution_count_subq = (
                select(func.count(AccountExecution.id))
                .where(
                    and_(
                        AccountExecution.snap_account_id == SnapchatAccount.id,
                        AccountExecution.type == ExecutionTypeEnum.QUICK_ADDS,
                        AccountExecution.status == StatusEnum.DONE,
                    )
                )
                .scalar_subquery()
            )
            exec_count_condition = execution_count_subq >= 2

            # Combine the conditions with OR: either the stats record qualifies,
            # or if no stats record exists then there must be at least 2 matching executions.
            query = query.filter(
                or_(
                    stats_condition,
                    and_(
                        no_stats_condition,
                        exec_count_condition
                    )
                )
            )

        # --- Optional Pagination ---
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

        # --- Execute Query ---
        snapchat_accounts = query.all()

        # --- If we do NOT want executions, or no accounts, just return them ---
        if not include_executions or not snapchat_accounts:
            return snapchat_accounts

        account_ids = [acct.id for acct in snapchat_accounts]

        # (b) Create a subquery with row_number() to rank each execution by start_time DESC
        subq = (
            db.query(
                AccountExecution.id.label("ae_id"),
                AccountExecution.snap_account_id.label("acct_id"),
                func.row_number()
                    .over(
                    partition_by=AccountExecution.snap_account_id,
                    order_by=AccountExecution.start_time.desc()
                )
                    .label("rn")
            )
                .filter(AccountExecution.snap_account_id.in_(account_ids))
                .subquery()
        )

        # (c) Join back to AccountExecution, filtering where rn <= 3
        top_executions = (
            db.query(AccountExecution)
                .join(subq, AccountExecution.id == subq.c.ae_id)
                .filter(subq.c.rn <= 3)
                # optional order_by for consistent results (not strictly required)
                .order_by(AccountExecution.snap_account_id, AccountExecution.start_time.desc())
                .all()
        )

        execs_by_acct = defaultdict(list)
        for ex in top_executions:
            execs_by_acct[ex.snap_account_id].append(ex)

        # Attach the top 3 to each SnapchatAccount *without* triggering lazy load:
        for acct in snapchat_accounts:
            # Directly overwrite the attribute in the instance’s __dict__, bypassing lazy loading.
            raw_execs = execs_by_acct.get(acct.id, [])
            # Make sure AccountExecutionSimpleResponse has `orm_mode = True` or `from_attributes = True`
            pydantic_execs = [AccountExecutionSimpleResponse.from_orm(e) for e in raw_execs]

            # Overwrite the relationship field with the Pydantic list
            acct.__dict__["account_executions"] = pydantic_execs

        return snapchat_accounts


    @staticmethod
    def get_account_by_id(db: Session, account_id: int) -> Optional[SnapchatAccount]:
        """
        Retrieves a Snapchat account by its ID.
        """
        return db.query(SnapchatAccount).filter(SnapchatAccount.id == account_id).first()

    @staticmethod
    def create_accounts_from_string(db: Session,
                                    agency_id:int,
                                    data: str,
                                    account_source: Optional[str] = None,
                                    model_id: Optional[int] = None,
                                    chatbot_id: Optional[int] = None,
                                    workflow_id: Optional[int] = None,
                                    trigger_execution: bool = False,
                                    pattern: Optional[str] = None
                                    ) -> List[SnapchatAccount]:
        """
        Creates Snapchat accounts from a large string input and assigns proxies, models, and chatbots based on the least usage.
        """
        from app.celery_tasks import ExecutionTaskManager
        accounts = []
        errors = []

        if pattern:
            SnapchatAccountUtils.validate_patter(pattern, [
                "two_fa_secret",
                "proxy",
                "username",
                "password",
                "email",
                "email_password",
                "creation_date",
                "snapchat_link"
            ])

        # Fetch proxies, models, and chatbots with their current usage count
        proxies = (
            db.query(Proxy, func.count(SnapchatAccount.id).label("account_count"))
                .outerjoin(SnapchatAccount, Proxy.id == SnapchatAccount.proxy_id)
                .filter(Proxy.agency_id == agency_id)
                .group_by(Proxy.id)
                .order_by(func.count(SnapchatAccount.id).asc())  # Sort by least usage
                .all()
        )
        if not proxies:
            raise ValueError("No proxies available in the system.")

        models = (
            db.query(Model, func.count(SnapchatAccount.id).label("account_count"))
                .outerjoin(SnapchatAccount, Model.id == SnapchatAccount.model_id)
                .filter(Model.agency_id == agency_id)
                .group_by(Model.id)
                .order_by(func.count(SnapchatAccount.id).asc())  # Sort by least usage
                .all()
        )
        if not models:
            raise ValueError("No models available in the system.")

        chatbots = (
            db.query(ChatBot, func.count(SnapchatAccount.id).label("account_count"))
                .outerjoin(SnapchatAccount, ChatBot.id == SnapchatAccount.chatbot_id)
                .filter(ChatBot.agency_id == agency_id)
                .group_by(ChatBot.id)
                .order_by(func.count(SnapchatAccount.id).asc())  # Sort by least usage
                .all()
        )
        if not chatbots:
            raise ValueError("No Chatbots available in the system.")

        # Initialize usage tracking
        proxy_usage = {proxy.id: count for proxy, count in proxies}
        model_usage = {model.id: count for model, count in models}
        chatbot_usage = {chatbot.id: count for chatbot, count in chatbots}

        proxy_pool = list(proxy_usage.keys())  # List of proxy IDs
        model_pool = list(model_usage.keys())
        chatbot_pool = list(chatbot_usage.keys())

        for index, line in enumerate(data.splitlines()):
            try:
                fields = {}
                if pattern:
                    fields = SnapchatAccountUtils.parse_account_linev2(line.strip(), index, pattern)
                else:
                    cleaned_line = re.sub(r'[\t:]+', ' ', line.strip())
                    fields = SnapchatAccountUtils.parse_account_line(cleaned_line, index)
                two_fa_secret = fields.get("two_fa_secret")
                proxy = fields.get("proxy")
                username = fields.get("username")
                password = fields.get("password")
                email = fields.get("email")
                email_password = fields.get("email_password")
                creation_date = fields.get("creation_date")
                snapchat_link = fields.get("snapchat_link")

                if two_fa_secret and len(two_fa_secret) != 32:
                    raise ValueError(
                        f"Invalid two_fa_secret length on line {index + 1}: Expected 32 characters, got {len(two_fa_secret)}"
                    )

                # Assign the account to resources with the least usage
                assigned_proxy_id = None
                if proxy:
                    existing_proxy = db.query(Proxy).filter_by(host=proxy.split(":")[0],
                                                                       port=proxy.split(":")[1]).first()
                    if existing_proxy:
                        assigned_proxy_id = existing_proxy.id
                    else:
                        assigned_proxy_id = proxy_pool[0]
                else:
                    assigned_proxy_id = proxy_pool[0]
                assigned_model_id = model_id or model_pool[0]
                assigned_chatbot_id = chatbot_id or chatbot_pool[0]

                # Create SnapchatAccount object
                account = SnapchatAccount(
                    username=username,
                    password=password,
                    snapchat_link=snapchat_link,
                    two_fa_secret=two_fa_secret,
                    creation_date=creation_date,
                    proxy_id=assigned_proxy_id,
                    model_id=assigned_model_id,
                    chatbot_id=assigned_chatbot_id,
                    workflow_id=workflow_id,
                    account_source=account_source or 'EXTERNAL',
                    email=email,
                    email_password=email_password,
                    agency_id=agency_id
                )
                db.add(account)
                accounts.append(account)

                # Update usage tracking
                proxy_usage[assigned_proxy_id] += 1
                model_usage[assigned_model_id] += 1
                chatbot_usage[assigned_chatbot_id] += 1

                # Re-sort pools
                proxy_pool = sorted(proxy_pool, key=lambda proxy_id: proxy_usage[proxy_id])
                model_pool = sorted(model_pool, key=lambda model_id: model_usage[model_id])
                chatbot_pool = sorted(chatbot_pool, key=lambda chatbot_id: chatbot_usage[chatbot_id])
            except IntegrityError as e:
                db.rollback()
                errors.append(
                    f"Constraint violation on line {index + 1}: {line}. Error: {str(e.orig)}"
                )
            except Exception as e:
                errors.append(f"Error on line {index + 1}: {line}. Error: {str(e)}")

        # Commit valid accounts to the database
        try:
            db.commit()
            for account in accounts:  # Ensure all IDs are available
                db.refresh(account)

            if trigger_execution:
                configuration_map = {
                    "starting_delay": 120
                }
                new_execution = Execution(
                    type=ExecutionTypeEnum.CHECK_CONVERSATIONS,
                    triggered_by="SYSTEM",
                    configuration=configuration_map,
                    status=StatusEnum.STARTED,
                    agency_id=agency_id
                )
                db.add(new_execution)
                db.commit()
                db.refresh(new_execution)
                created_account_ids = [account.id for account in accounts]
                ExecutionTaskManager.execute_task_celery.delay(new_execution.id, created_account_ids)
        except IntegrityError as e:
            db.rollback()
            errors.append(f"Database commit failed due to a constraint violation: {str(e.orig)}")

        if errors:
            raise ValueError(f"Some accounts could not be processed:\n" + "\n".join(errors))

        return accounts

    @staticmethod
    def update_account(db: Session, account_id: int, payload: dict) -> SnapchatAccount:
        account = db.query(SnapchatAccount).filter(SnapchatAccount.id == account_id).first()
        if not account:
            raise ValueError("Snapchat account not found")

        for key, value in payload.items():
            if hasattr(account, key):
                # Special handling for the `status` field
                if key == "status":
                    try:
                        # Convert the value to the enum
                        value = AccountStatusEnum[value.upper()]
                    except KeyError:
                        raise ValueError(f"Invalid status value: {value}")

                setattr(account, key, value)
            else:
                raise ValueError(f"Invalid field: {key}")
        if account.status not in {AccountStatusEnum.RECENTLY_INGESTED, AccountStatusEnum.GOOD_STANDING, AccountStatusEnum.CAPTCHA}:
            account.proxy_id = None
        try:
            db.commit()
            db.refresh(account)
        except Exception as e:
            db.rollback()  # Rollback if any error occurs
            raise ValueError(f"Failed to update account: {e}")

        return account

    @staticmethod
    def update_account_by_username(db: Session, username: str, update_data: dict):
        """
        Updates a Snapchat account by its username with the provided fields.
        """
        account = db.query(SnapchatAccount).filter(SnapchatAccount.username == username).first()
        if not account:
            return None

        for key, value in update_data.items():
            if hasattr(account, key):
                setattr(account, key, value)
            else:
                raise ValueError(f"Invalid field: {key}")

        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def create_and_attach_cookies(db: Session, username: str, data: dict):
        # Lookup the account based on the username
        account = db.query(SnapchatAccount).filter(SnapchatAccount.username == username).first()
        if not account:
            return None  # If account is not found, return None

        if account.cookies:
            # Replace the data in the existing cookies record
            account.cookies.data = data
            db.commit()
            db.refresh(account.cookies)
        else:
            # Create new cookies and associate it with the account
            new_cookie = Cookies(
                data=data,
                snapchat_account_id=account.id  # Use correct foreign key field here
            )
            db.add(new_cookie)
            db.commit()  # Commit the transaction to save the new cookie
            db.refresh(new_cookie)  # Refresh the instance to get the updated data
            account.cookies = new_cookie  # This associates the cookie with the account
            db.commit()  # Commit the changes

        # Return the updated account (including the new/updated cookie)
        return account

    @staticmethod
    def get_account_by_username(db: Session, username: str):
        return db.query(SnapchatAccount).filter(SnapchatAccount.username == username).first()

    @staticmethod
    def get_account_edit_data(db: Session, agency_id:int, account_id: int) -> SnapchatAccountEditResponse:
        """
        Fetch all data necessary for the edit page of a Snapchat account.
        """
        # Fetch the account details
        account = db.query(SnapchatAccount).filter(SnapchatAccount.id == account_id).first()
        if not account:
            raise ValueError("Snapchat account not found.")

        proxies = db.query(Proxy).filter(Proxy.agency_id==agency_id).all()

        models = db.query(Model).filter(Model.agency_id==agency_id).all()

        chat_bots = db.query(ChatBot).filter(ChatBot.agency_id==agency_id).all()

        workflows = db.query(Workflow).filter(Workflow.agency_id==agency_id).all()

        tags = db.query(SnapchatAccount.tags).filter(SnapchatAccount.agency_id == agency_id).distinct().all()

        unique_tags = set(tag for row in tags for tag in (row.tags or []))

        statuses = [status.name for status in AccountStatusEnum]

        return SnapchatAccountEditResponse(
            account=SnapchatAccountResponseV2.from_orm(account),
            proxies=[ProxySimpleResponse.from_orm(proxy) for proxy in proxies],
            models=[ModelResponse.from_orm(model) for model in models],
            chat_bots=[ChatBotResponse.from_orm(chat_bot) for chat_bot in chat_bots],
            statuses=statuses,
            tags=list(unique_tags),
            workflows=[WorkflowSimplifiedNameResponse.from_orm(workflow) for workflow in workflows],
        )

    @staticmethod
    def get_all_distinct_tags(db: Session, agency_id:int) -> List[str]:
        """
        Retrieve all distinct tags from Snapchat accounts and workflow steps.
        :param db: SQLAlchemy Session object.
        :return: List of distinct tags.
        """
        # Tags from SnapchatAccount
        snapchat_tags_query = (
            db.query(func.distinct(func.unnest(SnapchatAccount.tags)))
            .filter(SnapchatAccount.agency_id == agency_id)
            .all()
        )
        snapchat_tags = [tag[0] for tag in snapchat_tags_query if tag[0] is not None]

        # Tags from WorkflowStep (action_value where action_type is ADD_TAG or REMOVE_TAG)
        workflow_tags_query = (
            db.query(func.distinct(WorkflowStep.action_value))
            .filter(
                WorkflowStep.action_type.in_([WorkflowStepTypeEnum.ADD_TAG, WorkflowStepTypeEnum.REMOVE_TAG]),
                Workflow.agency_id == agency_id
            )
            .all()
        )
        workflow_tags = [tag[0] for tag in workflow_tags_query if tag[0] is not None]

        # Combine and return unique tags from both sources
        all_tags = sorted(set(snapchat_tags + workflow_tags))
        return list(all_tags)

    @staticmethod
    def get_snapchat_account_statuses(db: Session) -> list[str]:
        """
        Service to retrieve all unique statuses from the SnapchatAccount table.
        """
        # # Query distinct statuses
        # statuses = db.execute(
        #     select(distinct(SnapchatAccount.status))
        # ).scalars().all()
        #
        # # Convert Enum values to string if necessary
        # return [status.name for status in statuses]
        return [status.value for status in AccountStatusEnum]

    @staticmethod
    def get_snapchat_account_sources(db: Session, agency_id: int) -> list[str]:
        """
        Service to retrieve all unique account sources from the SnapchatAccount table,
        filtered by the given agency_id.
        """
        stmt = (
            select(distinct(SnapchatAccount.account_source))
            .where(SnapchatAccount.agency_id == agency_id)
        )
        sources = db.execute(stmt).scalars().all()

        # Convert Enum values to string if necessary
        return sources

    @staticmethod
    def get_accounts_for_termination(
            db: Session,
            agency_id:int
    ) -> List[SnapchatAccount]:
        excluded_statuses = [
            AccountStatusEnum.RECENTLY_INGESTED,
            AccountStatusEnum.GOOD_STANDING,
            AccountStatusEnum.CAPTCHA,
            AccountStatusEnum.TERMINATED,
        ]

        query = db.query(SnapchatAccount).filter(
            ~SnapchatAccount.status.in_(excluded_statuses),
            SnapchatAccount.agency_id == agency_id
        ).order_by(asc(SnapchatAccount.status))

        return query.all()

    @staticmethod
    def terminate_accounts(db: Session, account_ids: List[int]) -> int:
        """
        Marks all accounts with the given IDs as TERMINATED.
        """
        result = db.query(SnapchatAccount).filter(SnapchatAccount.id.in_(account_ids)).update(
            {SnapchatAccount.status: AccountStatusEnum.TERMINATED},
            synchronize_session="fetch",
        )
        db.commit()
        return result

    @staticmethod
    def get_snap_id_for_account(snapchat_account: SnapchatAccount):
        if snapchat_account.snapchat_id:
            return snapchat_account.snapchat_id
        if snapchat_account.snapchat_account_login and snapchat_account.snapchat_account_login.user_id:
            return snapchat_account.snapchat_account_login.user_id
        return None

    @staticmethod
    def bulk_update_accounts(
            db: Session,
            account_ids: List[int],
            status: Optional[str] = None,
            tags_to_add: Optional[List[str]] = None,
            tags_to_remove: Optional[List[str]] = None,
            model_id: Optional[int] = None,
            chat_bot_id: Optional[int] = None
    ) -> int:
        """
        Bulk update the provided fields on each SnapchatAccount in account_ids.
        Returns the number of accounts actually updated.
        """
        if not account_ids:
            return 0  # or raise an exception

        accounts = db.query(SnapchatAccount).filter(SnapchatAccount.id.in_(account_ids)).all()
        if not accounts:
            raise ValueError("No Snapchat accounts found with the given IDs.")

        updated_count = 0

        for account in accounts:
            if status is not None:
                try:
                    new_status = AccountStatusEnum(status)
                    account.status = new_status
                except ValueError:
                    raise ValueError(f"Invalid status value: {status}")

            if tags_to_add:
                if account.tags is None:
                    account.tags = []

                existing = set(account.tags)
                new = set(tags_to_add)
                account.tags = list(existing.union(new))

            if tags_to_remove and account.tags:
                remaining = [tag for tag in account.tags if tag not in tags_to_remove]
                account.tags = remaining

            if model_id is not None:
                account.model_id = model_id

            if chat_bot_id is not None:
                account.chatbot_id = chat_bot_id

            updated_count += 1

        db.commit()
        return updated_count

