from datetime import datetime

from sqlalchemy.orm import Session
from app.database import engine
from app.schemas.cookies import Cookies
from app.schemas.device import Device
from app.schemas.proxy import Proxy
from app.schemas.snapchat_account import SnapchatAccount
from app.services.airtable_service import AirtableService


class AirtableImporterService:
    BASE_ID = 'appiaCnT5CjmEukDq'
    TABLE_NAME = 'tblmuTTidcm3zJDSL'
    API_KEY_SECRET_NAME = 'AIRTABLE_API_KEY'

    def __init__(self):
        """
        Initializes the AirtableImporterService with the AirtableService instance.
        """
        self.airtable_service = AirtableService(
            base_id=self.BASE_ID,
            table_name=self.TABLE_NAME,
            api_key_secret_name=self.API_KEY_SECRET_NAME
        )

    def import_objects(self):
        """
        Imports objects from the Airtable view 'Stage 4 - AI Chatting' and stores them in the database.

        :return: A list of SnapchatAccount objects saved to the database.
        """
        view_name = 'Stage 4 - AI Chatting'
        records = self.airtable_service.get_records_from_view(view_name)

        snapchat_accounts = []
        # Start a new database session
        session = Session(bind=engine)

        try:
            for index, record in enumerate(records):
                fields = record.get("fields", {})

                try:
                    # Safely get data with defaults or handle missing fields
                    username = fields.get("Username")
                    password = fields.get("Password")
                    snapchat_link = fields.get("Snapchat Link")
                    two_fa_secret = fields.get("TWOFA_SECRET")
                    creation_date = fields.get("Creation Date")

                    if not username or not password or not snapchat_link:
                        raise ValueError(
                            f"Record {index + 1} is missing required fields: Username, Password, or Snapchat Link.")

                    # Parse creation date safely
                    creation_date_parsed = datetime.strptime(creation_date,
                                                             "%Y-%m-%d") if creation_date else datetime.utcnow()

                    # Create SnapchatAccount
                    account = SnapchatAccount(
                        username=username,
                        password=password,
                        snapchat_link=snapchat_link,
                        two_fa_secret=two_fa_secret,
                        creation_date=creation_date_parsed
                    )

                    # Handle Proxy creation (check for duplicates)
                    proxy_username = fields.get("Proxy_Username", [None])[0]
                    proxy_password = fields.get("Proxy_Password", [None])[0]
                    proxy_host = fields.get("Proxy_Host", [None])[0]

                    proxy = None
                    if proxy_username and proxy_password and proxy_host:
                        # Check if proxy already exists
                        proxy = session.query(Proxy).filter_by(
                            proxy_username=proxy_username,
                            proxy_password=proxy_password,
                            host=proxy_host
                        ).first()

                        # If no existing proxy is found, create a new one
                        if not proxy:
                            proxy = Proxy(
                                proxy_username=proxy_username,
                                proxy_password=proxy_password,
                                host=proxy_host
                            )
                            session.add(proxy)  # Add to session to ensure it's persisted

                        # Associate the proxy with the SnapchatAccount
                        account.proxy = proxy

                    # Create Device if field exists
                    device_data = fields.get("Device")
                    if device_data:
                        device = Device(data=device_data)
                        account.device = device

                    # Create Cookies if field exists
                    cookies_data = fields.get("Cookies")
                    if cookies_data:
                        cookies = Cookies(data=cookies_data)
                        account.cookies = cookies

                    # Add account to the session
                    session.add(account)
                    snapchat_accounts.append(account)

                except Exception as record_error:
                    print(f"Error processing record {index + 1}: {record_error}")

            session.commit()
            print(f"Successfully imported and stored {len(snapchat_accounts)} Snapchat accounts.")

        except Exception as e:
            session.rollback()
            print(f"Transaction failed: {e}")
        finally:
            session.close()  # Always close the session

        return snapchat_accounts
