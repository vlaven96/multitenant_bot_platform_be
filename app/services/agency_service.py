from sqlalchemy.orm import Session, joinedload

from app.celery_tasks import EmailTaskManager
from app.config import settings, email_settings
from app.dtos.agency_dtos import AgencyCreate
from app.schemas import Agency, User
from app.schemas.subscription import Subscription, SubscriptionStatus
from app.utils.security import hash_password, generate_random_password
import uuid
from fastapi_mail import MessageSchema, FastMail
from datetime import datetime, timedelta
import jwt

class AgencyService:

    @staticmethod
    def get_all_agencies(db: Session):
        return db.query(Agency).options(joinedload(Agency.subscription)).all()

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
    def create_agency_with_invitation(db, agency_data: AgencyCreate, background_tasks):
        # Check if an agency with the same name exists
        existing_agency = db.query(Agency).filter(Agency.name == agency_data.name).first()
        if existing_agency:
            raise ValueError("Agency already exists")
        # Create the agency
        agency = Agency(name=agency_data.name)
        db.add(agency)
        db.commit()
        db.refresh(agency)

        subscription = Subscription(
            agency_id=agency.id,
            status=SubscriptionStatus.AVAILABLE,
            renewed_at=datetime.utcnow(),
            days_available=7,
            number_of_sloths=5,
            price=0.00,
            turned_off_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Generate an invitation token (includes agency_id, admin_email, and role)
        token = AgencyService.generate_invite_token(agency, agency_data.agency_email, agency_data.admin_role)

        # Construct the registration link
        frontent_url = settings.frontend_url
        registration_link = f"{frontent_url}/register?token={token}"
        EmailTaskManager.send_email_task.delay(agency_data.agency_email, agency.name, registration_link)

        return agency

    @staticmethod
    def invite_user_to_agency(db: Session, agency_id: int, email: str):
        # Retrieve the agency using the provided agency_id
        agency = db.query(Agency).filter(Agency.id == agency_id).first()

        if not agency:
            raise ValueError("Agency not found.")

        email_exists = db.query(User).filter(User.email == email).first()
        if email_exists:
            raise ValueError("Email is already associated with an agency.")

        # Generate an invitation token, assuming the invited user is a regular user.
        token = AgencyService.generate_invite_token(agency, email, "USER")

        # Construct the registration link using the correct frontend URL.
        frontend_url = settings.frontend_url
        registration_link = f"{frontend_url}/register?token={token}"

        # Send the invitation email using the email task manager.
        EmailTaskManager.send_email_task.delay(email, agency.name, registration_link)

        return True

    @staticmethod
    def generate_invite_token(agency: Agency, email: str, role: str) -> str:
        """
        Generates a JWT token for inviting a user (Admin or User) to an agency.
        Role can be either "ADMIN" or "USER".
        """
        payload = {
            "agency_id": agency.id,  # Assign the user to the agency
            "email": email,  # Email of the invited user
            "role": role.upper(),  # Normalize role to uppercase for consistency
            "exp": datetime.utcnow() + timedelta(hours=24),  # Token expiration
            "type": "user_invitation"  # Updated token type for clarity
        }
        token = jwt.encode(payload, email_settings.SECRET_KEY, algorithm=email_settings.ALGORITHM)
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
        fm = FastMail(email_settings.mail_config)
        background_tasks.add_task(fm.send_message, message)
