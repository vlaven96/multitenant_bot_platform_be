# app/routers/jobs.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import Query
from app.database import get_db
from app.dtos.job_dtos.job_create_request import JobCreateRequest
from app.dtos.job_dtos.job_response import JobResponse
from app.dtos.job_dtos.job_simplified_response import JobSimplifiedResponse
from app.dtos.job_dtos.job_update_request import JobUpdateRequest
from app.dtos.job_status_update_request import JobStatusUpdateRequest
from app.dtos.snapchat_account_simple_response import SnapchatAccountSimpleResponse
from app.models.job_status_enum import JobStatusEnum
from app.services.job_service import JobsService
from app.utils.security import get_agency_id, check_subscription_available

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_new_job(job_create: JobCreateRequest, db: Session = Depends(get_db),
                   agency_id: int = Depends(get_agency_id), subscription = Depends(check_subscription_available),):
    """
    Endpoint to create a new job.
    """
    return JobsService.create_job(db, agency_id, job_create)


@router.get("/", response_model=List[JobResponse])
def read_jobs(status_filters: Optional[List[JobStatusEnum]] = Query(None),
              db: Session = Depends(get_db),
              agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve a list of jobs, optionally filtered by status.
    """
    return JobsService.list_jobs(db, agency_id, status_filters)


@router.get("/simplified", response_model=List[JobSimplifiedResponse])
def read_jobs_simplified(
        db: Session = Depends(get_db),
        agency_id: int = Depends(get_agency_id),
):
    """
    Endpoint to retrieve a simplified list of jobs (id and name only).
    """
    jobs = JobsService.list_jobs_simplified(db, agency_id)
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def read_job(job_id: int, db: Session = Depends(get_db),
             agency_id: int = Depends(get_agency_id), ):
    """
    Endpoint to retrieve a specific job by its ID.
    """
    return JobsService.get_job(db, job_id)


@router.put("/{job_id}", response_model=JobResponse)
def update_existing_job(job_id: int, job_update: JobUpdateRequest, db: Session = Depends(get_db),
                        agency_id: int = Depends(get_agency_id), subscription = Depends(check_subscription_available)):
    """
    Endpoint to update an existing job's details.
    """
    return JobsService.update_job(db, job_id, job_update)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_job(job_id: int, db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to perform a soft delete of a job by its ID.
    """
    JobsService.delete_job(db, job_id)
    return


@router.post("/{job_id}/restore", response_model=JobResponse, status_code=status.HTTP_200_OK)
def restore_job_endpoint(job_id: int, db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to restore a stopped job by its ID.
    """
    return JobsService.restore_job(db, job_id)


@router.patch("/{job_id}/status", response_model=JobResponse, status_code=status.HTTP_200_OK)
def update_job_status(job_id: int,
                      status_update_request: JobStatusUpdateRequest, db: Session = Depends(get_db),
                      agency_id: int = Depends(get_agency_id), subscription = Depends(check_subscription_available),):
    """
    Endpoint to update the status of a job.
    """
    return JobsService.update_job_status(db, job_id, status_update_request.status_update)


@router.get("/{job_id}/accounts", response_model=List[SnapchatAccountSimpleResponse])
def get_snapchat_accounts(job_id: int, db: Session = Depends(get_db), agency_id: int = Depends(get_agency_id)):
    """
    Endpoint to retrieve all Snapchat accounts matching the given job's statuses, tags, and sources.
    """
    return JobsService.get_snapchat_accounts_for_job(db, job_id)
