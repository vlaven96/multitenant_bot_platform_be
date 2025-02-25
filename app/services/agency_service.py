from sqlalchemy.orm import Session

from app.celery_tasks import EmailTaskManager
from app.config import settings
from app.dtos.agency_dtos import AgencyCreate
from app.schemas import Agency, User
from app.utils.security import hash_password, generate_random_password
import uuid
from fastapi_mail import MessageSchema, FastMail
from datetime import datetime, timedelta
import jwt

class AgencyService:

    @staticmethod
    def get_all_agencies(db: Session):
        return db.query(Agency).all()

    @staticmethod
    def get_agency_by_id(db: Session, agency_id: int):
        return db.query(Agency).filter(Agency.id == agency_id).first()

    @staticmethod
    def create_agency(db: Session, agency_data: AgencyCreate):
        # Check if agency name is unique
        existing_agency = db.query(Agency).filter(Agency.name == agency_data.name).first()
        if existing_agency:
            raise ValueError("Agency with this name already exists.")

        # Create the new agency
        new_agency = Agency(name=agency_data.name)
        db.add(new_agency)
        db.commit()
        db.refresh(new_agency)
        password = generate_random_password()
        # Create an admin user for this agency
        admin_user = User(
            username=f"admin_{new_agency.id}",
            email=f"admin_{new_agency.id}@example.com",
            password=hash_password(password),  # Store hashed password
            role="ADMIN",
            agency_id=new_agency.id
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        return {"agency": new_agency, "admin_username": admin_user.username, "admin_password": password}

    @staticmethod
    def create_agency_with_invitation(db, agency_data: AgencyCreate, background_tasks, request):
        # Check if an agency with the same name exists
        existing_agency = db.query(Agency).filter(Agency.name == agency_data.name).first()
        if existing_agency:
            raise ValueError("Agency already exists")
        # Create the agency
        agency = Agency(name=agency_data.name)
        db.add(agency)
        db.commit()
        db.refresh(agency)

        # Generate an invitation token (includes agency_id, admin_email, and role)
        token = AgencyService.generate_admin_invite_token(agency, agency_data.agency_email, agency_data.admin_role)

        # Construct the registration link
        registration_link = f"{request.base_url}auth/complete-admin-registration?token={token}"
        EmailTaskManager.send_email_task.delay(agency_data.agency_email, agency.name, registration_link)

        return agency

    @staticmethod
    def generate_admin_invite_token(agency: Agency, admin_email: str, role: str) -> str:
        payload = {
            "agency_id": agency.id,
            "admin_email": admin_email,
            "role": role,  # e.g., "admin"
            "exp": datetime.utcnow() + timedelta(hours=24),  # Valid for 24 hours
            "type": "admin_invite"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token

    @staticmethod
    def send_admin_invite_email(recipient: str, agency_name: str, registration_link: str, background_tasks):
        message = MessageSchema(
            subject="Complete Your Admin Registration",
            recipients=[recipient],
            body=(
                f"Hello,\n\nYour agency '{agency_name}' has been registered successfully.\n"
                f"Please complete your admin registration by clicking the link below:\n{registration_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            subtype="plain"
        )
        fm = FastMail(settings.mail_config)
        background_tasks.add_task(fm.send_message, message)
