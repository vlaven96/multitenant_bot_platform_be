from app.dtos.statistics.daily_account_stats_dto import DailyAccountStatsDTO
from app.dtos.statistics.snapchat_account_score_dto import SnapchatAccountScoreDTO
from app.dtos.statistics.snapchat_account_stats_response import SnapchatAccountStatsDTO, AccountExecutionDTO, \
    StatusChangeDTO, \
    SnapchatAccountTimelineStatisticsDTO, ModelSnapchatAccountStatsDTO
from app.models.account_status_enum import AccountStatusEnum
from app.models.chat_bot_type_enum import ChatBotTypeEnum
from app.models.operation_models.compute_statistics_result import ComputeStatisticsResult
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.status_enum import StatusEnum
from app.schemas import SnapchatAccount, SnapchatAccountStatusLog, Model
from app.schemas.executions.account_execution import AccountExecution
from app.schemas.snapchat_account_stats import SnapchatAccountStats
from app.services.snapchat_account_service import SnapchatAccountService
from sqlalchemy import func, cast, Integer
from sqlalchemy.sql import exists, and_
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta, datetime
from typing import Dict, Optional
from sqlalchemy import desc
from typing import List

import logging

logger = logging.getLogger(__name__)


class SnapchatAccountStatisticsService:
    @staticmethod
    def _get_stats_from_cupidbot(cupid_token: str, snap_account_id: str) -> dict:
        """
        Fetches statistics from CupidBot's API for the given Snapchat account ID.

        :param cupid_token: The access token for CupidBot.
        :param snap_account_id: The Snapchat account ID.
        :return: A dictionary containing statistics values extracted from the response.
        """

        def safe_int(value):
            """Safely converts a value to an integer. Returns 0 if conversion fails."""
            try:
                return int(value.split()[0]) if isinstance(value, str) and value.split()[0].isdigit() else int(value)
            except (ValueError, TypeError, IndexError):
                return 0

        url = "https://cupidbot-382905.uc.r.appspot.com/api/getAnalytics"
        params = {
            "accessToken": cupid_token,
            "app": "snapchat",
            "version": "0.19.68",
            "preset_id": "98845",
            "presetName": "Leah default",
            "viewingApps": "snapchat",
            "viewingAccountID": snap_account_id,
        }
        headers = {"Authorization": f"Bearer {cupid_token}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            analytics_data = response.json()

            # Extract relevant values from rows
            stats = {
                "chatbot_conversations": safe_int(analytics_data["rows"][0]["values"][0]),
                "conversations_charged": safe_int(analytics_data["rows"][1]["values"][0]),
                "cta_conversations": safe_int(analytics_data["rows"][2]["values"][0]),
                "cta_shared_links": safe_int(analytics_data["rows"][3]["values"][0]),
                "conversions_from_cta_links": safe_int(analytics_data["rows"][4]["values"][0]),
                "total_conversions": safe_int(analytics_data["rows"][5]["values"][0]),
            }
            return stats
        except Exception as e:
            print(f"Failed to fetch or process CupidBot statistics: {str(e)}")
            return {}

    @staticmethod
    def _get_statistics_from_executions(db: Session, snapchat_account) -> dict:
        """
        Retrieves statistics from account executions for a given Snapchat account.

        :param db: Database session.
        :param snapchat_account: The Snapchat account instance.
        :return: A dictionary containing statistics.
        """
        # Initialize the result dictionary with default values
        stats = {
            "total_conversations": 0,
            "quick_ads_sent": 0,
            "total_executions": 0,
            "successful_executions": 0,
        }

        try:
            # Fetch the most recent CHECK_CONVERSATIONS execution marked as DONE
            conversation_execution = (
                db.query(AccountExecution)
                .filter(
                    AccountExecution.snap_account_id == snapchat_account.id,
                    AccountExecution.type == ExecutionTypeEnum.CHECK_CONVERSATIONS,
                    AccountExecution.status == StatusEnum.DONE,
                )
                .order_by(AccountExecution.id.desc())
                .first()
            )

            # If found, update conversations count
            if conversation_execution and "conversations" in conversation_execution.result:
                stats["total_conversations"] = conversation_execution.result["conversations"] or 0

            # Sum of 'total_sent_requests' from QUICK_ADDS executions marked as DONE
            quick_ads_result_stats = (
                db.query(
                    func.sum(
                        cast(AccountExecution.result.op('->>')('total_sent_requests'), Integer)
                    ).label('quick_ads_total_sent_requests'),
                    func.sum(
                        cast(AccountExecution.result.op('->>')('rejected_count'), Integer)
                    ).label('quick_ads_rejected_count')
                )
                .filter(
                    AccountExecution.snap_account_id == snapchat_account.id,
                    AccountExecution.type == ExecutionTypeEnum.QUICK_ADDS,
                    AccountExecution.status == StatusEnum.DONE,
                )
                .first()
            )
            consume_leads_stats = (
                db.query(
                    func.sum(
                        cast(AccountExecution.result.op('->>')('total_sent_requests'), Integer)
                    ).label('consume_sent_requests')
                )
                .filter(
                    AccountExecution.snap_account_id == snapchat_account.id,
                    AccountExecution.type == ExecutionTypeEnum.CONSUME_LEADS,
                    AccountExecution.status == StatusEnum.DONE,
                )
                .first()
            )
            generate_leads_stats = (
                db.query(
                    func.sum(
                        cast(AccountExecution.result.op('->>')('generated_leads'), Integer)
                    ).label('total_generated_leads'),
                    func.sum(
                        cast(AccountExecution.result.op('->>')('rejected_count'), Integer)
                    ).label('generate_rejected_count')
                )
                .filter(
                    AccountExecution.snap_account_id == snapchat_account.id,
                    AccountExecution.type == ExecutionTypeEnum.GENERATE_LEADS,
                    AccountExecution.status == StatusEnum.DONE,
                )
                .first()
            )

            # Extract the results with a fallback to 0

            stats["quick_ads_sent"] = (quick_ads_result_stats.quick_ads_total_sent_requests or 0) + \
                                      (consume_leads_stats.consume_sent_requests or 0)

            stats["rejected_count"] = (quick_ads_result_stats.quick_ads_rejected_count or 0) + \
                                      (generate_leads_stats.generate_rejected_count or 0)

            stats["generated_leads"] = generate_leads_stats.total_generated_leads or 0

            # Count total executions (any status)
            stats["total_executions"] = (
                db.query(AccountExecution)
                .filter(AccountExecution.snap_account_id == snapchat_account.id)
                .count()
            )

            # Count successful executions (DONE)
            stats["successful_executions"] = (
                db.query(AccountExecution)
                .filter(
                    AccountExecution.snap_account_id == snapchat_account.id,
                    AccountExecution.status == StatusEnum.DONE,
                )
                .count()
            )

        except Exception as e:
            # Log or handle the exception appropriately
            # For example, you could do logger.exception("Error fetching statistics") instead
            print(f"An error occurred while fetching statistics: {str(e)}")

        return stats

    @staticmethod
    def compute_statistics(
            db: Session,
            snapchat_account: SnapchatAccount,
            account_execution_id: int,
    ) -> ComputeStatisticsResult:
        """
        Computes and stores statistics for a given Snapchat account.

        :param db: The database session.
        :param snapchat_account: The Snapchat account instance.
        :param account_execution_id: The ID of the current account execution.
        :return: A ComputeStatisticsResult indicating success or failure.
        """
        try:
            snap_account_id = SnapchatAccountService.get_snap_id_for_account(snapchat_account)
            if not snap_account_id:
                logger.error("Current account has no executions registered in the platform, can't compute statistics.")
                return ComputeStatisticsResult(
                    success=False,
                    message="Current account has no executions registered in the platform, can't compute statistics."
                )
            merged_stats = {
                "snapchat_account_id": snapchat_account.id
            }

            # Initialize statistics object
            stats = SnapchatAccountStats(
                snapchat_account_id=snapchat_account.id,
            )

            cupid_stats = None
            if snapchat_account.chat_bot.type == ChatBotTypeEnum.CUPID_BOT:
                cupid_stats = SnapchatAccountStatisticsService._get_stats_from_cupidbot(
                    snapchat_account.chat_bot.token, snap_account_id
                )

            if cupid_stats:
                merged_stats.update({
                    "chatbot_conversations": cupid_stats.get("chatbot_conversations", 0),
                    "conversations_charged": cupid_stats.get("conversations_charged", 0),
                    "cta_conversations": cupid_stats.get("cta_conversations", 0),
                    "cta_shared_links": cupid_stats.get("cta_shared_links", 0),
                    "conversions_from_cta_links": cupid_stats.get("conversions_from_cta_links", 0),
                    "total_conversions": cupid_stats.get("total_conversions", 0),
                })

            executions_stats = SnapchatAccountStatisticsService._get_statistics_from_executions(db, snapchat_account)
            if executions_stats:
                merged_stats.update({
                    "total_conversations": executions_stats.get("total_conversations", 0),
                    "quick_ads_sent": executions_stats.get("quick_ads_sent", 0),
                    "successful_executions": executions_stats.get("successful_executions", 0),
                    "total_executions": executions_stats.get("total_executions", 0),
                    "rejected_total": executions_stats.get("rejected_count", 0),
                    "generated_leads": executions_stats.get("generated_leads", 0)
                })

            # Save or update statistics in the database
            existing_stats = (
                db.query(SnapchatAccountStats)
                .filter(SnapchatAccountStats.snapchat_account_id == snapchat_account.id)
                .one_or_none()
            )
            snapchat_account.snapchat_id = snap_account_id
            db.add(snapchat_account)
            if existing_stats:
                # Update existing statistics
                for field, value in merged_stats.items():
                    setattr(existing_stats, field, value)
                db.add(existing_stats)
            else:
                # Create new statistics record
                db.add(stats)
            db.commit()

            return ComputeStatisticsResult(
                success=True,
                message="Statistics computed and stored successfully."
            )
        except Exception as e:
            message = f"Error on collecting statistics: {e}"
            logger.error(message)
            return ComputeStatisticsResult(
                success=False,
                message=message
            )

    @staticmethod
    def get_user_statistics(db: Session, snapchat_account_id: int) -> dict:
        """
        Retrieves statistics for a user.

        :param db: Database session.
        :param user_id: The ID of the user.
        :return: A dictionary containing the user's statistics.
        """
        try:
            # Fetch the user's Snapchat account
            snapchat_account = (
                db.query(SnapchatAccount)
                .filter(SnapchatAccount.id == snapchat_account_id)
                .one_or_none()
            )

            if not snapchat_account:
                return {
                    "success": False,
                    "message": "No Snapchat account found for the given user.",
                    "statistics": {},
                }

            # Fetch the associated SnapchatAccountStats
            stats = (
                db.query(SnapchatAccountStats)
                .filter(SnapchatAccountStats.snapchat_account_id == snapchat_account.id)
                .one_or_none()
            )

            if not stats:
                return {
                    "success": False,
                    "message": "No statistics found for the given Snapchat account.",
                    "statistics": {},
                }

            # Return the statistics as a dictionary
            return SnapchatAccountStatsDTO(
                total_conversations=stats.total_conversations,
                chatbot_conversations=stats.chatbot_conversations,
                conversations_charged=stats.conversations_charged,
                cta_conversations=stats.cta_conversations,
                cta_shared_links=stats.cta_shared_links,
                conversions_from_cta_links=stats.conversions_from_cta_links,
                total_conversions=stats.total_conversions,
                quick_ads_sent=stats.quick_ads_sent,
                total_executions=stats.total_executions,
                successful_executions=stats.successful_executions,
                rejected_total=stats.rejected_total,
                message="Stats retrieved successfully",
                success=True
            )

        except Exception as e:
            return SnapchatAccountStatsDTO(
                success=False,
                message=f"An error occurred while retrieving statistics: {str(e)}",
            )

    @staticmethod
    def get_user_timeline_statistics(db: Session, snapchat_account_id: int):
        """
        Retrieves detailed statistics for a given Snapchat account.

        :param db: Database session.
        :param snapchat_account_id: ID of the Snapchat account.
        :return: SnapchatAccountStatisticsDTO containing account statistics.
        """
        # Fetch the Snapchat account
        snapchat_account = db.query(SnapchatAccount).filter(SnapchatAccount.id == snapchat_account_id).one_or_none()

        if not snapchat_account:
            raise ValueError(f"No Snapchat account found with ID {snapchat_account_id}")

        # Fetch account executions
        account_executions = db.query(AccountExecution).filter(
            AccountExecution.snap_account_id == snapchat_account_id,
            ~AccountExecution.type.in_(["STATUS_CHECK", "COMPUTE_STATISTICS"])
        ).all()

        # Fetch status change logs
        status_logs = db.query(SnapchatAccountStatusLog).filter(
            SnapchatAccountStatusLog.snapchat_account_id == snapchat_account_id
        ).all()

        # Map account executions to DTOs
        account_executions_dto = [
            AccountExecutionDTO(type=execution.type.name, start_time=execution.start_time)
            for execution in account_executions
        ]

        # Map status logs to DTOs
        status_changes_dto = [
            StatusChangeDTO(new_status=log.new_status.name, changed_at=log.changed_at) for log in status_logs
        ]

        # Return the assembled DTO
        return SnapchatAccountTimelineStatisticsDTO(
            creation_date=snapchat_account.creation_date,
            ingestion_date=snapchat_account.added_to_system_date,
            account_executions=account_executions_dto,
            status_changes=status_changes_dto,
        )

    @staticmethod
    def get_overall_statistics(db: Session, agency_id: int) -> SnapchatAccountStatsDTO:
        """
        Retrieves overall statistics for Snapchat accounts filtered by agency.

        :param db: Database session.
        :param agency_id: ID of the agency to filter statistics.
        :return: A SnapchatAccountStatsDTO containing overall statistics.
        """
        try:
            # Aggregate statistics for Snapchat accounts by joining with SnapchatAccount
            aggregated_stats = (
                db.query(
                    func.sum(SnapchatAccountStats.total_conversations).label("total_conversations"),
                    func.sum(SnapchatAccountStats.chatbot_conversations).label("chatbot_conversations"),
                    func.sum(SnapchatAccountStats.conversations_charged).label("conversations_charged"),
                    func.sum(SnapchatAccountStats.cta_conversations).label("cta_conversations"),
                    func.sum(SnapchatAccountStats.cta_shared_links).label("cta_shared_links"),
                    func.sum(SnapchatAccountStats.conversions_from_cta_links).label("conversions_from_cta_links"),
                    func.sum(SnapchatAccountStats.total_conversions).label("total_conversions"),
                    func.sum(SnapchatAccountStats.quick_ads_sent).label("quick_ads_sent"),
                    func.sum(SnapchatAccountStats.total_executions).label("total_executions"),
                    func.sum(SnapchatAccountStats.successful_executions).label("successful_executions"),
                    func.sum(SnapchatAccountStats.rejected_total).label("rejected_total"),
                    func.sum(SnapchatAccountStats.generated_leads).label("generated_leads")
                )
                .join(SnapchatAccount, SnapchatAccount.id == SnapchatAccountStats.snapchat_account_id)
                .filter(SnapchatAccount.agency_id == agency_id)
                .one()
            )

            # Check if there are any statistics
            if not aggregated_stats or all(stat is None for stat in aggregated_stats):
                return SnapchatAccountStatsDTO(
                    success=False,
                    message="No statistics found for any Snapchat accounts.",
                )

            # Return aggregated statistics as a DTO
            return SnapchatAccountStatsDTO(
                total_conversations=aggregated_stats.total_conversations or 0,
                chatbot_conversations=aggregated_stats.chatbot_conversations or 0,
                conversations_charged=aggregated_stats.conversations_charged or 0,
                cta_conversations=aggregated_stats.cta_conversations or 0,
                cta_shared_links=aggregated_stats.cta_shared_links or 0,
                conversions_from_cta_links=aggregated_stats.conversions_from_cta_links or 0,
                total_conversions=aggregated_stats.total_conversions or 0,
                quick_ads_sent=aggregated_stats.quick_ads_sent or 0,
                total_executions=aggregated_stats.total_executions or 0,
                successful_executions=aggregated_stats.successful_executions or 0,
                rejected_total=aggregated_stats.rejected_total or 0,
                generated_leads=aggregated_stats.generated_leads or 0
            )

        except Exception as e:
            return SnapchatAccountStatsDTO(
                success=False,
                message=f"An error occurred while retrieving overall statistics: {str(e)}",
            )

    @staticmethod
    def get_overall_statistics_grouped_by_model(db: Session, agency_id:int) -> Dict[int, ModelSnapchatAccountStatsDTO]:
        """
        Retrieves overall statistics for all users, grouped by model, including model names.

        :param db: Database session.
        :return: A dictionary where keys are model IDs, and values contain model name and statistics.
        """
        try:
            # Aggregate statistics grouped by model_id, including model name
            aggregated_stats = (
                db.query(
                    SnapchatAccount.model_id,
                    Model.name.label("model_name"),  # Fetch model name
                    func.sum(SnapchatAccountStats.total_conversations).label("total_conversations"),
                    func.sum(SnapchatAccountStats.chatbot_conversations).label("chatbot_conversations"),
                    func.sum(SnapchatAccountStats.conversations_charged).label("conversations_charged"),
                    func.sum(SnapchatAccountStats.cta_conversations).label("cta_conversations"),
                    func.sum(SnapchatAccountStats.cta_shared_links).label("cta_shared_links"),
                    func.sum(SnapchatAccountStats.conversions_from_cta_links).label("conversions_from_cta_links"),
                    func.sum(SnapchatAccountStats.total_conversions).label("total_conversions"),
                    func.sum(SnapchatAccountStats.quick_ads_sent).label("quick_ads_sent"),
                    func.sum(SnapchatAccountStats.total_executions).label("total_executions"),
                    func.sum(SnapchatAccountStats.successful_executions).label("successful_executions"),
                    func.sum(SnapchatAccountStats.rejected_total).label("rejected_total"),
                    func.sum(SnapchatAccountStats.generated_leads).label("generated_leads")
                )
                .join(SnapchatAccount, SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id)
                .filter(SnapchatAccount.agency_id == agency_id)
                .outerjoin(Model, Model.id == SnapchatAccount.model_id)  # Join with Model to get model name
                .group_by(SnapchatAccount.model_id, Model.name)  # Group by model_id and model name
                .all()
            )

            # Prepare the result dictionary
            model_statistics = {}

            for row in aggregated_stats:
                model_id = row.model_id if row.model_id is not None else "Unknown"
                model_name = row.model_name if row.model_name is not None else "Unknown"

                model_statistics[model_id] = {
                    "model_name": model_name,
                    "statistics": SnapchatAccountStatsDTO(
                        total_conversations=row.total_conversations or 0,
                        chatbot_conversations=row.chatbot_conversations or 0,
                        conversations_charged=row.conversations_charged or 0,
                        cta_conversations=row.cta_conversations or 0,
                        cta_shared_links=row.cta_shared_links or 0,
                        conversions_from_cta_links=row.conversions_from_cta_links or 0,
                        total_conversions=row.total_conversions or 0,
                        quick_ads_sent=row.quick_ads_sent or 0,
                        total_executions=row.total_executions or 0,
                        successful_executions=row.successful_executions or 0,
                        rejected_total=row.rejected_total or 0,
                        generated_leads=row.generated_leads or 0
                    ),
                }

            return model_statistics

        except Exception as e:
            return {
                "error": f"An error occurred while retrieving overall statistics grouped by model: {str(e)}"
            }

    @staticmethod
    def get_accounts_by_status(db: Session) -> dict:
        """
        Retrieves the count of Snapchat accounts grouped by status.
        """
        results = (
            db.query(
                SnapchatAccount.status,
                func.count(SnapchatAccount.id).label("count")
            )
            .group_by(SnapchatAccount.status)
            .all()
        )

        # Convert results to a dictionary: {status: count, ...}
        status_counts = {status.value: count for status, count in results}
        total_accounts = sum(status_counts.values())

        return {
            "total_accounts": total_accounts,
            "accounts_by_status": status_counts,
        }

    @staticmethod
    def get_average_time_for_all_statuses(db: Session, agency_id) -> Dict[str, str]:
        """
        Calculates the average time spent in each status across all accounts filtered by agency.

        :param db: Database session.
        :param agency_id: The agency id to filter accounts.
        :return: A dictionary mapping status names to average time spent as timedeltas.
        """
        sql = text("""
                SELECT
                    current_status,
                    AVG(EXTRACT(epoch FROM (next_changed_at - changed_at))) AS avg_seconds
                FROM (
                    SELECT
                        sal.changed_at,
                        sal.new_status AS current_status,
                        LEAD(sal.changed_at) OVER (PARTITION BY sal.snapchat_account_id ORDER BY sal.changed_at) AS next_changed_at
                    FROM snapchat_account_status_log sal
                    JOIN snapchat_account sa ON sal.snapchat_account_id = sa.id
                    WHERE sa.agency_id = :agency_id
                ) sub
                WHERE next_changed_at IS NOT NULL
                GROUP BY current_status
            """)

        results = db.execute(sql, {"agency_id": agency_id}).fetchall()
        avg_times = {}

        for row in results:
            status = row.current_status  # Enum or string
            avg_seconds = row.avg_seconds
            status_str = str(status) if isinstance(status, AccountStatusEnum) else status
            avg_times[status_str] = SnapchatAccountStatisticsService.format_timedelta_to_days_hours(
                timedelta(seconds=float(avg_seconds)) if avg_seconds is not None else timedelta(0)
            )

        return avg_times

    @staticmethod
    def format_timedelta_to_days_hours(td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        days = total_seconds // 86400  # 86400 seconds in a day
        hours = (total_seconds % 86400) // 3600  # 3600 seconds in an hour

        parts = []
        if days:
            parts.append(f"{days} day" if days == 1 else f"{days} days")
        if hours:
            parts.append(f"{hours} hour" if hours == 1 else f"{hours} hours")

        return ", ".join(parts) if parts else "0 hours"

    @staticmethod
    def get_average_time_by_source_for_status_exit(db: Session, agency_id: int) -> Dict[str, str]:
        """
        Calculates the average time for accounts from all sources to transition
        out of RECENTLY_INGESTED or GOOD_STANDING statuses from account creation,
        filtered by agency.

        :param db: Database session.
        :param agency_id: The agency id to filter accounts.
        :return: A dictionary mapping each account source to average time (formatted as a timedelta).
        """
        sql = text("""
            WITH first_exit AS (
                SELECT
                    sa.id AS account_id,
                    sa.account_source,
                    MIN(exit_log.changed_at) AS first_exit_time,
                    sa.added_to_system_date
                FROM snapchat_account sa
                JOIN snapchat_account_status_log exit_log 
                    ON sa.id = exit_log.snapchat_account_id
                WHERE sa.agency_id = :agency_id
                  AND exit_log.new_status NOT IN ('RECENTLY_INGESTED', 'GOOD_STANDING')
                  AND exit_log.changed_at > sa.added_to_system_date
                GROUP BY sa.id, sa.account_source, sa.added_to_system_date
            )
            SELECT
                account_source,
                AVG(EXTRACT(epoch FROM (first_exit_time - added_to_system_date))) AS avg_seconds
            FROM first_exit
            GROUP BY account_source
        """)

        results = db.execute(sql, {"agency_id": agency_id}).fetchall()
        avg_times: Dict[str, Optional[timedelta]] = {}

        for row in results:
            source = str(row.account_source)
            avg_seconds = row.avg_seconds
            avg_times[source] = timedelta(seconds=float(avg_seconds)) if avg_seconds is not None else None

        formatted: Dict[str, str] = {}
        for source, duration in avg_times.items():
            if duration is not None:
                formatted[source] = SnapchatAccountStatisticsService.format_timedelta_to_days_hours(duration)
            else:
                formatted[source] = "No data"

        return formatted

    @staticmethod
    def get_execution_counts_by_source_until_status_change(db: Session, agency_id: int) -> Dict[str, int]:
        """
        Calculates the number of account executions for each account source until
        the account transitions out of RECENTLY_INGESTED or GOOD_STANDING, filtered by agency.

        :param db: Database session.
        :param agency_id: The agency ID to filter accounts.
        :return: A dictionary mapping each account source to the number of executions.
        """
        sql = text("""
            WITH first_exit AS (
                SELECT
                    sa.id AS account_id,
                    sa.account_source,
                    MIN(exit_log.changed_at) AS first_exit_time
                FROM snapchat_account sa
                JOIN snapchat_account_status_log exit_log 
                    ON sa.id = exit_log.snapchat_account_id
                WHERE sa.agency_id = :agency_id
                  AND exit_log.new_status NOT IN ('RECENTLY_INGESTED', 'GOOD_STANDING')
                  AND exit_log.changed_at > sa.added_to_system_date
                GROUP BY sa.id, sa.account_source
            )
            SELECT
                fe.account_source,
                COUNT(ae.id) AS execution_count
            FROM account_execution ae
            JOIN first_exit fe ON ae.snap_account_id = fe.account_id
            WHERE ae.start_time < fe.first_exit_time
            GROUP BY fe.account_source
        """)

        results = db.execute(sql, {"agency_id": agency_id}).fetchall()
        execution_counts = {str(row.account_source): row.execution_count for row in results}
        return execution_counts

    @staticmethod
    def select_top_n_snapchat_accounts_optimized(session: Session,
                                                 agency_id: int,
                                                 n: int,
                                                 weight_rejecting_rate: float,
                                                 weight_conversation_rate: float,
                                                 weight_conversion_rate: float):
        """
        Optimized selection of top n Snapchat accounts using database-level computations,
        filtered by agency.
        """
        # Subquery to compute metrics, filtering by agency_id
        metrics_subquery = session.query(
            SnapchatAccountStats.id.label('stat_id'),
            SnapchatAccount.id.label('account_id'),
            func.coalesce(
                SnapchatAccountStats.rejected_total /
                func.nullif(
                    SnapchatAccountStats.rejected_total + SnapchatAccountStats.quick_ads_sent + SnapchatAccountStats.generated_leads,
                    0
                ),
                0
            ).label('rejecting_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversations /
                func.nullif(SnapchatAccountStats.quick_ads_sent, 0),
                0
            ).label('conversation_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversions /
                func.nullif(SnapchatAccountStats.conversations_charged, 0),
                0
            ).label('conversion_rate')
        ).join(SnapchatAccount).filter(SnapchatAccount.agency_id == agency_id).subquery()

        # Aggregates for normalization
        aggregates = session.query(
            func.max(metrics_subquery.c.rejecting_rate).label('max_rejecting_rate'),
            func.max(metrics_subquery.c.conversation_rate).label('max_conversation_rate'),
            func.max(metrics_subquery.c.conversion_rate).label('max_conversion_rate')
        ).one()

        max_rejecting_rate = aggregates.max_rejecting_rate or 1
        max_conversation_rate = aggregates.max_conversation_rate or 1
        max_conversion_rate = aggregates.max_conversion_rate or 1

        # Final query with score calculation, ensuring the agency filter is applied
        final_query = session.query(
            SnapchatAccount,
            (
                    weight_rejecting_rate * (metrics_subquery.c.rejecting_rate / max_rejecting_rate) +
                    weight_conversation_rate * (metrics_subquery.c.conversation_rate / max_conversation_rate) +
                    weight_conversion_rate * (metrics_subquery.c.conversion_rate / max_conversion_rate)
            ).label('score')
        ).join(SnapchatAccountStats, SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id
               ).join(metrics_subquery, metrics_subquery.c.stat_id == SnapchatAccountStats.id
                      ).filter(SnapchatAccount.agency_id == agency_id
                               ).order_by(desc('score')).limit(n)

        # Execute query and fetch results
        results = final_query.all()

        # Extract SnapchatAccount objects
        top_n_snapchat_accounts = [result.SnapchatAccount for result in results]

        return top_n_snapchat_accounts

    @staticmethod
    def get_all_snapchat_accounts_with_scores(session: Session,
                                              agency_id: int,
                                              weight_rejecting_rate: float,
                                              weight_conversation_rate: float,
                                              weight_conversion_rate: float) -> List[SnapchatAccountScoreDTO]:
        """
        Retrieves all Snapchat accounts with their rejecting rate, conversation rate,
        total conversions, and computed score based on provided weights, filtered by agency.

        :param session: Database session.
        :param agency_id: The agency ID to filter accounts.
        :param weight_rejecting_rate: Weight for rejecting rate.
        :param weight_conversation_rate: Weight for conversation rate.
        :param weight_conversion_rate: Weight for conversion rate.
        :return: A list of dictionaries with Snapchat account details and calculated scores.
        """

        # Subquery to compute individual metrics per account, filtered by agency_id
        metrics_subquery = session.query(
            SnapchatAccountStats.id.label('stat_id'),
            SnapchatAccount.id.label('account_id'),
            SnapchatAccount.username.label('username'),  # Include username
            func.coalesce(
                SnapchatAccountStats.rejected_total /
                func.nullif(
                    SnapchatAccountStats.rejected_total + SnapchatAccountStats.quick_ads_sent + SnapchatAccountStats.generated_leads,
                    0
                ),
                0
            ).label('rejecting_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversations /
                func.nullif(SnapchatAccountStats.quick_ads_sent, 0),
                0
            ).label('conversation_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversions /
                func.nullif(SnapchatAccountStats.conversations_charged, 0),
                0
            ).label('conversion_rate')
        ).join(SnapchatAccount).filter(SnapchatAccount.agency_id == agency_id).subquery()

        # Aggregates for normalization
        aggregates = session.query(
            func.max(metrics_subquery.c.rejecting_rate).label('max_rejecting_rate'),
            func.max(metrics_subquery.c.conversation_rate).label('max_conversation_rate'),
            func.max(metrics_subquery.c.conversion_rate).label('max_conversion_rate')
        ).one()

        max_rejecting_rate = aggregates.max_rejecting_rate or 1
        max_conversation_rate = aggregates.max_conversation_rate or 1
        max_conversion_rate = aggregates.max_conversion_rate or 1

        # Final query to retrieve accounts with their metrics and computed score, filtered by agency_id
        final_query = session.query(
            SnapchatAccount.id.label('account_id'),
            SnapchatAccount.username.label('username'),
            metrics_subquery.c.rejecting_rate,
            metrics_subquery.c.conversation_rate,
            metrics_subquery.c.conversion_rate,
            (
                    weight_rejecting_rate * (metrics_subquery.c.rejecting_rate / max_rejecting_rate) +
                    weight_conversation_rate * (metrics_subquery.c.conversation_rate / max_conversation_rate) +
                    weight_conversion_rate * (metrics_subquery.c.conversion_rate / max_conversion_rate)
            ).label('score')
        ).join(
            SnapchatAccountStats, SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id
        ).join(
            metrics_subquery, metrics_subquery.c.stat_id == SnapchatAccountStats.id
        ).filter(SnapchatAccount.agency_id == agency_id
                 ).order_by(desc('score'))

        # Fetch results
        results = final_query.all()

        # Convert query results to list of dictionaries
        accounts_with_scores = [
            {
                "account_id": row.account_id,
                "username": row.username,
                "rejecting_rate": row.rejecting_rate or 0,
                "conversation_rate": row.conversation_rate or 0,
                "conversion_rate": row.conversion_rate or 0,
                "score": row.score or 0
            }
            for row in results
        ]

        return accounts_with_scores

    @staticmethod
    def get_daily_account_stats(session: Session, agency_id: int, days: int) -> List[DailyAccountStatsDTO]:
        """
        Fetches daily account statistics over a given number of days, filtered by agency.

        Args:
            session (Session): SQLAlchemy session object.
            agency_id (int): Agency ID to filter accounts.
            days (int): Number of past days to fetch data for.

        Returns:
            List[Tuple[datetime, int, int]]: A list of tuples containing:
                - Day (datetime)
                - Count of distinct accounts ran (int)
                - Total quick ads sent (int)
        """
        query = (
            session.query(
                func.date(AccountExecution.start_time).label("day"),
                func.count(func.distinct(AccountExecution.snap_account_id)).label("accounts_ran"),
                func.sum(
                    cast(
                        func.coalesce(AccountExecution.result.op("->>")("total_sent_requests"), "0"),
                        Integer
                    )
                ).label("total_quick_ads_sent"),
            )
            .join(SnapchatAccount, SnapchatAccount.id == AccountExecution.snap_account_id)
            .filter(
                AccountExecution.start_time >= datetime.utcnow() - timedelta(days=days),
                AccountExecution.type.in_([ExecutionTypeEnum.QUICK_ADDS, ExecutionTypeEnum.CONSUME_LEADS]),
                SnapchatAccount.agency_id == agency_id
            )
            .group_by(func.date(AccountExecution.start_time))
            .order_by(func.date(AccountExecution.start_time))
        )

        return query.all()

    @staticmethod
    def count_daily_chatbot_run_accounts(
            db: Session,
            agency_id: int
    ) -> int:
        """
        Counts the number of Snapchat accounts matching the given filters.

        Args:
            db (Session): SQLAlchemy session object.
            agency_id (int): The agency ID to filter accounts.

        Returns:
            int: Count of matching Snapchat accounts.
        """
        query = db.query(func.count(SnapchatAccount.id))

        statuses = [AccountStatusEnum.GOOD_STANDING]
        query = query.filter(SnapchatAccount.status.in_(statuses))

        # Filter by agency_id
        query = query.filter(SnapchatAccount.agency_id == agency_id)

        query = query.filter(
            exists().where(
                and_(
                    AccountExecution.snap_account_id == SnapchatAccount.id,
                    AccountExecution.type == ExecutionTypeEnum.QUICK_ADDS,
                    AccountExecution.status == StatusEnum.DONE,
                )
            )
        )

        return query.scalar()

    @staticmethod
    def get_accounts_by_thresholds(
            session: Session,
            max_rejecting_rate_threshold: float,
            min_conversation_rate_threshold: float,
            min_conversion_rate_threshold: float,
            statuses: Optional[List[AccountStatusEnum]] = None,
            tags: Optional[List[str]] = None,
            sources: Optional[List[str]] = None,
    ) -> List[SnapchatAccount]:
        """
        Retrieves SnapchatAccount objects that respect the given thresholds for
        rejecting rate, conversation rate, and conversion rate.

        :param session: Database session.
        :param max_rejecting_rate_threshold: Maximum allowed rejecting rate.
        :param min_conversation_rate_threshold: Minimum required conversation rate.
        :param min_conversion_rate_threshold: Minimum required conversion rate.
        :return: A list of SnapchatAccount objects meeting the criteria.
        """
        if not statuses:
            statuses = [AccountStatusEnum.GOOD_STANDING, AccountStatusEnum.CAPTCHA]
        # Subquery to compute individual metrics per account
        metrics_subquery = session.query(
            SnapchatAccountStats.id.label('stat_id'),
            SnapchatAccount.id.label('account_id'),
            func.coalesce(
                SnapchatAccountStats.rejected_total /
                func.nullif(
                    SnapchatAccountStats.rejected_total +
                    SnapchatAccountStats.quick_ads_sent +
                    SnapchatAccountStats.generated_leads, 0
                ), 0
            ).label('rejecting_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversations /
                func.nullif(SnapchatAccountStats.quick_ads_sent, 0), 0
            ).label('conversation_rate'),
            func.coalesce(
                SnapchatAccountStats.total_conversions /
                func.nullif(SnapchatAccountStats.conversations_charged, 0), 0
            ).label('conversion_rate')
        ).join(SnapchatAccount).subquery()

        # Build the final query selecting SnapchatAccount objects
        final_query = session.query(SnapchatAccount).join(
            SnapchatAccountStats, SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id
        ).join(
            metrics_subquery, metrics_subquery.c.stat_id == SnapchatAccountStats.id
        ).filter(
            metrics_subquery.c.rejecting_rate <= max_rejecting_rate_threshold,
            metrics_subquery.c.conversation_rate >= min_conversation_rate_threshold,
            metrics_subquery.c.conversion_rate >= min_conversion_rate_threshold
        )

        filters = [
            metrics_subquery.c.rejecting_rate <= max_rejecting_rate_threshold,
            metrics_subquery.c.conversation_rate >= min_conversation_rate_threshold,
            metrics_subquery.c.conversion_rate >= min_conversion_rate_threshold
        ]

        # Add optional filters based on provided arguments
        if statuses:
            filters.append(SnapchatAccount.status.in_(statuses))
        if tags:
            # Assuming `tags` is a column that supports `.contains(...)`
            filters.append(SnapchatAccount.tags.contains(tags))
        if sources:
            filters.append(SnapchatAccount.account_source.in_(sources))

        # Apply all filters to the query
        final_query = final_query.filter(*filters)

        # Execute query and fetch SnapchatAccount results
        accounts_respecting_thresholds = final_query.all()

        accounts_without_stats_query = (
            session.query(SnapchatAccount)
            .outerjoin(
                SnapchatAccountStats,
                SnapchatAccountStats.snapchat_account_id == SnapchatAccount.id
            )
        )
        filters = []
        if statuses:
            filters.append(SnapchatAccount.status.in_(statuses))
        if tags:
            # Assuming `tags` is a column that supports `.contains(...)`
            filters.append(SnapchatAccount.tags.contains(tags))
        if sources:
            filters.append(SnapchatAccount.account_source.in_(sources))

        accounts_without_stats_query = accounts_without_stats_query.filter(*filters)
        accounts_without_stats = accounts_without_stats_query.all()
        return accounts_respecting_thresholds + accounts_without_stats
