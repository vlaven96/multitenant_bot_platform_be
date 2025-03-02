from sqlalchemy.orm import Session
from app.database import engine
from app.models.chat_bot_type_enum import ChatBotTypeEnum
from app.schemas.chatbot import ChatBot
from app.schemas.model import Model
from app.schemas.snapchat_account import SnapchatAccount
from app.schemas.user import User, UserRole
from sqlalchemy.future import select

from app.utils.security import hash_password

def create_global_admin():
    session = Session(bind=engine)
    global_admin = session.query(User).filter_by(role=UserRole.GLOBAL_ADMIN).first()
    if global_admin:
        print("Admin user already exists. Skipping creation.")
        session.close()
        return
    global_admin = User(
        username="global_admin",
        email="global_admin@gmail.com",
        password=hash_password("globaladminpassword"),
        role=UserRole.GLOBAL_ADMIN
    )
    session.add(global_admin)
    session.commit()
    session.close()

def create_default_admin():
    session = Session(bind=engine)

    # Check if an admin user already exists
    admin_exists = session.query(User).filter_by(is_admin=True).first()
    if admin_exists:
        print("Admin user already exists. Skipping creation.")
        session.close()
        return  # Exit if admin already exists

    # Create the default admin user
    admin_user = User(
        username="admin",
        email="admin@example.com",
        password=hash_password("adminpassword"),  # Securely hash the password
        is_admin=True,
        is_active=True
    )
    user = User(
        username="vladimir",
        email="vladimir@example.com",
        password=hash_password("userpassword"),  # Securely hash the password
        is_admin=False,
        is_active=True
    )
    session.add(admin_user)
    session.add(user)
    session.commit()
    session.close()

    print("Default admin user created: username='admin', password='adminpassword'")



def associate_accounts_with_model(model_name: str, onlyfans_url: str):
    """
    Create a new Model if it doesn't exist, and associate it with all SnapchatAccount records.

    :param db_session: AsyncSession instance for database operations.
    :param model_name: Name of the model to create.
    :param onlyfans_url: The OnlyFans URL for the model.
    """
    db_session = Session(bind=engine)
    try:
        # Check if the model already exists
        query = select(Model).where(Model.name == model_name)
        model = (db_session.execute(query)).scalars().first()

        query = select(Model).where(Model.name == "Angeles")
        model2 = (db_session.execute(query)).scalars().first()

        if not model:
            # Create a new model
            model = Model(name=model_name, onlyfans_url=onlyfans_url)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            print(f"Created new model '{model_name}' with ID: {model.id}")

        if not model2:
            # Create a new model
            model = Model(name="Angeles", onlyfans_url="https://onlyfans.com/angelespicy")
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            print(f"Created new model '{model_name}' with ID: {model.id}")

        # Fetch all SnapchatAccounts
        accounts_query = select(SnapchatAccount).where(SnapchatAccount.model_id == None)
        accounts = (db_session.execute(accounts_query)).scalars().all()

        # Associate accounts with the model
        for account in accounts:
            account.model_id = model.id
            print(f"Associated SnapchatAccount ID {account.id} with Model '{model_name}'")

        # Commit changes
        db_session.commit()
        print("Association process completed.")

    except Exception as e:
        print(f"Error during association process: {e}")
        db_session.rollback()

def associate_accounts_with_chatbot():
    """
    Create a new Model if it doesn't exist, and associate it with all SnapchatAccount records.

    :param db_session: AsyncSession instance for database operations.
    :param model_name: Name of the model to create.
    :param onlyfans_url: The OnlyFans URL for the model.
    """
    db_session = Session(bind=engine)
    try:
        # Check if the model already exists
        query = select(ChatBot).where(ChatBot.type == ChatBotTypeEnum.CUPID_BOT)
        model = (db_session.execute(query)).scalars().first()

        query = select(ChatBot).where(ChatBot.type == ChatBotTypeEnum.HOT_BOT)
        model2 = (db_session.execute(query)).scalars().first()

        if not model:
            # Create a new model
            model = ChatBot(type=ChatBotTypeEnum.CUPID_BOT, token="5cb75ec7721e3ed209fa22fc55480edf")
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            print(f"Created new model 'CupidBot' with ID: {model.id}")

        if not model2:
            # Create a new model
            model = ChatBot(type=ChatBotTypeEnum.HOT_BOT, token="TO_BE_PROVIDED")
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            print(f"Created new model 'CupidBot' with ID: {model.id}")

        # Fetch all SnapchatAccounts
        accounts_query = select(SnapchatAccount).where(SnapchatAccount.chatbot_id == None)
        accounts = (db_session.execute(accounts_query)).scalars().all()

        # Associate accounts with the model
        for account in accounts:
            account.chatbot_id = model.id
            print(f"Associated SnapchatAccount ID {account.id} with Chatbot 'CupidBot'")

        # Commit changes
        db_session.commit()
        print("Association process completed.")

    except Exception as e:
        print(f"Error during association process: {e}")
        db_session.rollback()
