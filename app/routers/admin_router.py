from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, List

from app.dtos.update_user_request import UpdateUserRequest
from app.dtos.user_response import UserResponse
from app.services.airtable_importer_service import AirtableImporterService
from app.utils.controller_utils import str_to_bool
from app.utils.security import get_admin_user
from sqlalchemy.orm import Session
from app.database import engine
from app.schemas.user import User
from pydantic import StrictBool


router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.put("/activate-user/{user_id}")
def activate_user(user_id: int, current_user: dict = Depends(get_admin_user)):
    # Ensure the current user is an admin
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can activate accounts.")

    session = Session(bind=engine)
    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        session.close()
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        session.close()
        raise HTTPException(status_code=400, detail="User account is already active")

    # Activate the user
    user.is_active = True
    session.commit()
    session.close()

    return {"message": f"User {user.username} has been activated successfully"}

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(lambda: Session(bind=engine)),
    is_active: Optional[str] = Query(None, description="Filter by active status"),
    username: Optional[str] = Query(None, description="Filter by username")
):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can access the user list.")

    query = db.query(User)

    # Convert the `is_active` query parameter to a boolean
    try:
        is_active_bool = str_to_bool(is_active)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Apply filters
    if is_active_bool is not None:
        query = query.filter(User.is_active == is_active_bool)

    if username:
        sanitized_username = username.strip()
        query = query.filter(User.username.ilike(f"%{sanitized_username}%"))

    users = query.all()
    db.close()

    return users

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    updates: UpdateUserRequest = Body(...),
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(lambda: Session(bind=engine)),
):
    """
    Updates user attributes. Admins can modify any user attribute (e.g., activate a user, update email).
    """
    # Ensure the current user is an admin
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can update user accounts.")

    # Retrieve the user by ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply updates to the user
    if updates.username:
        user.username = updates.username.strip()
    if updates.email:
        user.email = updates.email.strip()
    if updates.is_active is not None:
        user.is_active = updates.is_active
    if updates.is_admin is not None:
        user.is_admin = updates.is_admin

    # Commit changes to the database
    db.commit()
    db.refresh(user)  # Refresh the user object with updated values

    return user

@router.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    updates: UpdateUserRequest = Body(...),
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(lambda: Session(bind=engine)),
):
    """
    Partially updates a user's attributes.
    """
    # Ensure the current user is an admin
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can update user accounts.")

    # Retrieve the user by ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply updates to the user only for fields provided
    if updates.username is not None:
        user.username = updates.username.strip()
    if updates.email is not None:
        user.email = updates.email.strip()
    if updates.is_active is not None:
        user.is_active = updates.is_active
    if updates.is_admin is not None:
        user.is_admin = updates.is_admin

    # Commit the changes
    db.commit()
    db.refresh(user)  # Refresh the user object with updated values

    return user

airtable_importer = AirtableImporterService()

@router.post("/import-airtable")
def import_airtable_data(current_user: dict = Depends(get_admin_user)):
        """
        Triggers the import of data from Airtable.

        :param current_user: The currently authenticated admin user.
        :return: A response indicating the status of the import and the number of records retrieved.
        """
        if not current_user["is_admin"]:
            raise HTTPException(status_code=403, detail="Only admins can import Airtable data.")

        try:
            records = airtable_importer.import_objects()
            return {
                "message": f"Successfully imported {len(records)} records from Airtable.",
                "data": records
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to import data from Airtable: {str(e)}")