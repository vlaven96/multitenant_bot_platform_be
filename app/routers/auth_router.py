from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.dtos.login_request import LoginRequest
from app.dtos.register_user import RegisterUser
from app.dtos.user_create_request import UserCreateRequest
from app.schemas.user import User
from app.services.auth_service import AuthService
from app.utils.security import hash_password
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.jwt_handler import create_access_token
from app.utils.security import verify_password

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/register")
def register_user(user: RegisterUser):
    session = Session(bind=engine)

    # Check if user already exists
    if session.query(User).filter((User.email == user.email) | (User.username == user.username)).first():
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        is_admin=False
    )
    session.add(new_user)
    session.commit()
    session.close()

    return {"message": "User created successfully"}

    return {"message": "User created successfully"}

@router.post("/login")
def login_user(login_request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_request.username).first()

    if not user or not verify_password(login_request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,  # Include is_admin in the response
        "agency_id": user.agency_id
    }

@router.post("/complete-registration")
def complete_registration(user_data: UserCreateRequest, db: Session = Depends(get_db)):
    """
    Completes user registration using the invitation token.
    Calls the AuthService to handle the business logic.
    """
    try:
        response = AuthService.complete_registration(db,user_data)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))