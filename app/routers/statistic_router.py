from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db  # Replace with your actual database dependency
from app.dtos.snapchat_account_response import SnapchatAccountResponse, SnapchatAccountResponseV2
from app.dtos.statistics.daily_account_stats_dto import DailyAccountStatsDTO
from app.dtos.statistics.snapchat_account_score_dto import SnapchatAccountScoreDTO
from app.dtos.statistics.snapchat_account_stats_response import SnapchatAccountStatsDTO, ModelSnapchatAccountStatsDTO
from app.services.snapchat_account_statistics_service import SnapchatAccountStatisticsService
from app.utils.security import get_current_user, get_agency_id
from typing import Dict
from datetime import timedelta

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"]
)


@router.get("/", response_model=SnapchatAccountStatsDTO)
def get_user_statistics(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
                        agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve user statistics.

    :param user_id: The ID of the user.
    :param db: The database session.
    :return: SnapchatAccountStatsDTO containing the user's statistics.
    """
    statistics_dto = SnapchatAccountStatisticsService.get_overall_statistics(db, agency_id)

    return statistics_dto


@router.get("/grouped-by-model", response_model=Dict[int, ModelSnapchatAccountStatsDTO])
def get_statistics_grouped_by_model(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
                                    agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve overall statistics grouped by model.

    :param db: The database session.
    :return: A dictionary where keys are model IDs, and values contain model name and statistics.
    """
    statistics_by_model = SnapchatAccountStatisticsService.get_overall_statistics_grouped_by_model(db, agency_id)

    return statistics_by_model


@router.get("/statuses")
def get_user_statistics(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
                        agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve user statistics.

    :param user_id: The ID of the user.
    :param db: The database session.
    :return: SnapchatAccountStatsDTO containing the user's statistics.
    """
    statistics_dto = SnapchatAccountStatisticsService.get_average_time_for_all_statuses(db, agency_id)

    return statistics_dto


@router.get("/average-times-by-source", response_model=Dict[str, str])
def average_times_by_source_exit(db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve average time spent in RECENTLY_INGESTED and GOOD_STANDING
    statuses by account source until leaving those statuses.
    """
    try:
        avg_times: Dict[
            str, Dict[str, timedelta]] = SnapchatAccountStatisticsService.get_average_time_by_source_for_status_exit(db, agency_id)
        # Convert timedelta values to strings for JSON serialization
        formatted = {source: str(duration) for source, duration in avg_times.items() if duration is not None}
        return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-counts-by-source", response_model=Dict[str, int])
def execution_counts_by_source(db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve the number of executions by account source
    until leaving RECENTLY_INGESTED or GOOD_STANDING.
    """
    try:
        counts = SnapchatAccountStatisticsService.get_execution_counts_by_source_until_status_change(db, agency_id)
        return counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-snapchat-accounts", response_model=List[SnapchatAccountResponseV2])
def get_top_snapchat_accounts(
        n: int = 10,
        weight_rejecting_rate: float = 0.3,
        weight_conversation_rate: float = 0.4,
        weight_conversion_rate: float = 0.3,
        session: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id)
):
    """
    Retrieve top n Snapchat accounts based on weighted metrics.
    """
    # Call the selection algorithm with provided parameters
    top_accounts = SnapchatAccountStatisticsService.select_top_n_snapchat_accounts_optimized(
        session=session,
        agency_id=agency_id,
        n=n,
        weight_rejecting_rate=weight_rejecting_rate,
        weight_conversation_rate=weight_conversation_rate,
        weight_conversion_rate=weight_conversion_rate
    )

    # Convert ORM objects to response schema if necessary
    # Assuming SnapchatAccountResponse can be constructed from SnapchatAccount
    return top_accounts


@router.get("/accounts_with_score", response_model=List[SnapchatAccountScoreDTO])
def get_top_snapchat_accounts(
        weight_rejecting_rate: float = 0.3,
        weight_conversation_rate: float = 0.4,
        weight_conversion_rate: float = 0.3,
        session: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id)
):
    """
    Retrieve top n Snapchat accounts based on weighted metrics.
    """
    # Call the selection algorithm with provided parameters
    accounts_with_score = SnapchatAccountStatisticsService.get_all_snapchat_accounts_with_scores(
        session=session,
        agency_id=agency_id,
        weight_rejecting_rate=weight_rejecting_rate,
        weight_conversation_rate=weight_conversation_rate,
        weight_conversion_rate=weight_conversion_rate
    )

    return accounts_with_score


@router.get("/daily-stats", response_model=List[DailyAccountStatsDTO])
def get_daily_account_stats(
        days: int = 7,
        session: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id)
):
    """
    Retrieve top n Snapchat accounts based on weighted metrics.
    """
    # Call the selection algorithm with provided parameters
    accounts_with_score = SnapchatAccountStatisticsService.get_daily_account_stats(
        session=session,
        agency_id=agency_id,
        days=days
    )

    return accounts_with_score


@router.get("/daily-chatbot-runs", response_model=int)
def get_daily_account_stats(
        session: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id)
):
    """
    Retrieve top n Snapchat accounts based on weighted metrics.
    """
    # Call the selection algorithm with provided parameters
    accounts_with_score = SnapchatAccountStatisticsService.count_daily_chatbot_run_accounts(
        db=session,
        agency_id=agency_id
    )

    return accounts_with_score
