import time
from typing import Optional, Dict, Tuple, List
import json
import requests
import random
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.models.dpa_request_params import DPARequestParams
from app.models.operation_models.check_conversations_result import CheckConversationsResult
from app.models.operation_models.check_status_result import CheckStatusResult
from app.models.operation_models.consume_leads_config import ConsumeLeadsConfig
from app.models.operation_models.consume_leads_result import ConsumeLeadsResult
from app.models.operation_models.generate_leads_result import GenerateLeadsResult
from app.models.operation_models.quick_adds_result import QuickAddsResult
from app.models.operation_models.quick_ads_config import QuickAdsConfig
from app.models.operation_models.send_to_username_result import SendToUsernameResult
from app.schemas.device import Device
from app.schemas.snapchat_account import SnapchatAccount
from app.schemas.snapchat_account_login import SnapchatAccountLogin
from app.services.clients.snapkat_client import SnapkatClient
import os
from app.services.snapchat_account_validator_service import SnapchatAccountValidatorService
from app.utils.email_extractor_utils import EmailExtractorUtils
from app.utils.snapkat_utils import SnapkatUtils
import logging
logger = logging.getLogger(__name__)


class SnapchatService:
    def __init__(self, db: Session, use_residential_proxies: bool = False):
        """
        Initialize the Snapkat client manager.

        :param snapkat_api_key: API key for Snapkat.
        :param use_residential_proxies: Flag to enable residential proxies.
        """
        self.snapkat_api_key = os.getenv("SNAPKAT_API_KEY")
        self.use_residential_proxies = use_residential_proxies
        self.db = db

    def create_and_login_client(self, snapchat_account: SnapchatAccount) -> Optional[tuple]:
        """
        Create and log in a Snapkat client.

        :param snapchat_account: The Snapchat account object.
        :return: A tuple (logged_in_client, message). If unsuccessful, returns (None, error_message).
        """
        username: Optional[str] = snapchat_account.username
        password: Optional[str] = snapchat_account.password

        if not username or not password:
            error_message = f"Record {snapchat_account.id} is missing Username or Password."
            logger.error(error_message)
            return None, error_message

        proxies = SnapkatUtils.configure_proxies(snapchat_account.proxy)
        client = self._initialize_client(proxies)

        device: Optional[str] = snapchat_account.device.data if snapchat_account.device else None
        if not device:
            return self._create_device_and_login(client, snapchat_account)
        else:
            return self._login_with_existing_device(client, snapchat_account)

    def _initialize_client(self, proxies: Optional[Dict[str, str]]) -> SnapkatClient:
        """
        Initialize a Snapkat client with optional proxy settings.

        :param proxies: Proxy configuration, or None if no proxy is used.
        :return: An initialized Snapkat client.
        """
        client = SnapkatClient(snapkat_api_key=self.snapkat_api_key, proxies=proxies)

        if self.use_residential_proxies:
            try:
                residential_proxies = {
                    "http": "http://mr37042byUM:dpasnap2024_country-us@ultra.marsproxies.com:44443",
                    "https": "http://mr37042byUM:dpasnap2024_country-us@ultra.marsproxies.com:44443"
                }
                client.proxies = residential_proxies
            except Exception as e:
                logger.error(f"Error setting residential proxies: {str(e)}")
        return client

    def _create_device_and_login(self, client: SnapkatClient, snapchat_account: SnapchatAccount) -> Optional[tuple]:
        """
        Create a new device and log in the user.

        :param client: The Snapkat client.
        :param snapchat_account: The Snapchat account object.
        :return: A tuple (logged_in_client, message). If unsuccessful, returns (None, error_message).
        """
        root_message = "_create_device_and_login_"
        logger.info(f"Creating new device for user {snapchat_account.username}.")
        try:
            # Create a new device and attempt login
            device, message = self.create_device_and_login(
                client,
                snapchat_account,
                snapchat_account.username,
                snapchat_account.password,
                snapchat_account.two_fa_secret
            )

            if device is None:
                error_message = f"{root_message}-Failed to create or log in with a new device for user {snapchat_account.username}: {message}"
                logger.error(error_message)
                return None, error_message

            # Set the device in the client
            client.set_device(device)

            # Serialize and save the device
            device_json = json.dumps(client.device)
            self.update_record_device(snapchat_account, device_json)

            success_message = "Device created and login successful."
            logger.info(success_message)
            return client, success_message

        except Exception as e:
            error_message = f"{root_message}An unexpected error occurred while creating a device for user {snapchat_account.username}: {str(e)}"
            logger.error(error_message)
            return None, error_message

    def _login_with_existing_device(self, client: SnapkatClient, snapchat_account: SnapchatAccount) -> Optional[tuple]:
        """
        Log in using an existing device.

        :param client: The Snapkat client.
        :param record: The user record.
        :param device: JSON-encoded device data.
        :param username: The username of the user.
        :param password: The password of the user.
        :param twoFA_secret: The 2FA secret, if applicable.
        :return: A tuple (logged_in_client, message). If unsuccessful, returns (None, error_message).
        """
        try:
            parsed_device = json.loads(snapchat_account.device.data)
            client.set_device(parsed_device)
            logger.info(f"Using existing device for user {snapchat_account.username}: {parsed_device}")

            device, login_message = self.login(
                client,
                snapchat_account,
                snapchat_account.username,
                snapchat_account.password,
                snapchat_account.two_fa_secret
            )

            if device is None:
                error_message = f"Login failed for user {snapchat_account.username} with existing device: {login_message}"
                logger.error(error_message)
                return None, login_message

                # Successful login
            return client, "Login successful with existing device."

        except json.JSONDecodeError:
            err_msg = f"Invalid device data for user {snapchat_account.username}. Skipping."
            logger.error(err_msg)
            return None, err_msg

        return client, "Login successful with existing device."

    def create_device_and_login(self, client: SnapkatClient, snapchat_account: SnapchatAccount, username: str,
                                password: str,
                                twoFA_secret: Optional[str] = None) -> \
            Optional[tuple]:
        """
        Creates a new device for the Snapkat client and logs in the user.

        :param client: The Snapkat client instance.
        :param username: The username for the account.
        :param password: The password for the account.
        :param twoFA_secret: The two-factor authentication secret, if applicable.
        :return: The created device as a dictionary, or None if login fails or an error occurs.
        """
        root_message = "_child_create_device_and_login_"
        try:
            # Generate a device template from the client
            device = client.get_device_template()
            client.set_device(device)
            logger.info(f"Device created: {device}")

            # Attempt to log in the user with the new device
            device, login_message = self.login(client, snapchat_account, username, password, twoFA_secret)

            if device is None:
                logger.error(f"Login failed for user {username}. Reason: {login_message}")
                return None, root_message + login_message

            # Return the successfully created device
            return device, login_message

        except Exception as e:
            error_message = f"{root_message}An error occurred during device creation and login: {str(e)}"
            logger.info(error_message)
            return None, error_message

    def _check_if_login_exists(self, snapchat_account_login: Optional[SnapchatAccountLogin]) -> Optional[
        SnapchatAccountLogin]:
        """
        Checks if the SnapchatAccountLogin exists and is still valid.

        :param snapchat_account_login: The SnapchatAccountLogin object to check.
        :return: The SnapchatAccountLogin if it exists and is valid; otherwise, None.
        """
        if snapchat_account_login and snapchat_account_login.expires_at > datetime.utcnow():
            return snapchat_account_login
        return None

    def _update_snapchat_account_login(self, snapchat_account: SnapchatAccount, login_resp: dict):
        """
        Processes the login response and updates/creates the SnapchatAccountLogin instance.

        :param snapchat_account: The SnapchatAccount instance.
        :param login_resp: The response dictionary from the login attempt.
        :return: Tuple (bool, message): True if successful, False otherwise.
        """
        try:
            # Step 1: Validate and extract data from the login response
            if 'bootstrap_data' not in login_resp:
                raise KeyError("Missing 'bootstrap_data' in login response.")
            data = login_resp['bootstrap_data']

            if not data or 'user_session' not in data:
                raise KeyError("Missing 'user_session' in login_response['bootstrap_data'].")

            user_session = data['user_session']

            if 'snap_session_response' not in user_session:
                raise KeyError("Missing 'snap_session_response' in user_session.")
            access_tokens = user_session['snap_session_response']

            if 'snap_access_tokens' not in access_tokens or not access_tokens['snap_access_tokens']:
                raise KeyError("Missing or invalid 'snap_access_tokens' in snap_session_response.")

            # Step 2: Extract required fields
            access_token = access_tokens['snap_access_tokens'][0]['access_token']
            expires_in_seconds = int(access_tokens['snap_access_tokens'][0]['expires_in_seconds'])
            user_auth_token = user_session['auth_token']
            user_id = user_session["user_id"]
            mutable_username = user_session["mutable_username"]

            # Log extracted values
            logger.info(f"mutable_username: {mutable_username}")
            logger.info(f"user_id: {user_id}")
            logger.info(f"access_token: {access_token}")
            logger.info(f"user_auth_token: {user_auth_token}")

            # Step 3: Update or create SnapchatAccountLogin
            snapchat_account_login = (
                snapchat_account.snapchat_account_login
                if snapchat_account.snapchat_account_login
                else SnapchatAccountLogin()
            )

            snapchat_account_login.snap_account_id = snapchat_account.id  # Reference parent account
            snapchat_account_login.auth_token = user_auth_token
            snapchat_account_login.user_id = user_id
            snapchat_account_login.mutable_username = mutable_username
            snapchat_account_login.access_token = access_token
            snapchat_account_login.expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds - 6000)

            # Step 4: Attach SnapchatAccountLogin to SnapchatAccount if not already attached
            if not snapchat_account.snapchat_account_login:
                snapchat_account.snapchat_account_login = snapchat_account_login

            return True, "Login Processed Successfully"
        except KeyError as e:
            message = f"Missing expected key in login response: {str(e)}. The login response is: {login_resp}"
            logger.error(message)
            return False, message
        except Exception as e:
            message = f"An error occurred while processing login response: {str(e)}. The login response is: {login_resp}"
            logger.error(message)
            return False, message

    def login(self, client: SnapkatClient, snapchat_account: SnapchatAccount, username: str, password: str,
              twoFA_secret: Optional[str] = None) -> \
            Optional[tuple]:
        """
        Logs in the user and performs additional session setup.

        :param client: The Snapkat client instance.
        :param snapchat_account: The SnapchatAccount object to associate the login.
        :param username: The username for the account.
        :param password: The password for the account.
        :param twoFA_secret: The two-factor authentication secret, if applicable.
        :return: Tuple (device details, message), or (None, error message) if the login process fails.
        """
        root_message = "_login_"
        snapchat_account_login = self._check_if_login_exists(snapchat_account.snapchat_account_login)
        return_message = "Success Login"
        if not snapchat_account_login:
            login_resp, message = self.attempt_login_with_retries(client, snapchat_account, username, password, twoFA_secret)
            if not login_resp:
                return None, f"{root_message}Login failed: {message}"

            account_locked_data = login_resp.get('account_locked_data', {})
            if account_locked_data:
                human_readable_message = account_locked_data.get('human_readable_message', None)
                return_message = human_readable_message or str(login_resp)
                return None, root_message + return_message
            else:
                return_message = str(login_resp)
            response_update, process_message = self._update_snapchat_account_login(snapchat_account, login_resp)
            if not response_update:
                return None, root_message + process_message

        response, process_message = self.process_login_response(client, snapchat_account.snapchat_account_login)
        if not response:
            return None, f"{root_message}Failed to process login response: {process_message}"

        fidelius_argos_response, fidelius_message = self.handle_fidelius_and_argos(client)
        if not fidelius_argos_response:
            return None, root_message + fidelius_message

        return client.device, return_message

    def attempt_login_with_retries(self, client: SnapkatClient, snapchat_account: SnapchatAccount, username: str, password: str,
                                   twoFA_secret: Optional[str],
                                   retries: int = 3) -> Tuple[Optional[dict], str]:
        """
        Attempts to log in with retries in case of errors.

        :param client: The Snapkat client instance.
        :param username: The username for the account.
        :param password: The password for the account.
        :param twoFA_secret: The two-factor authentication secret, if applicable.
        :param retries: Number of retry attempts.
        :return: The login response dictionary, or None if all attempts fail.
        """
        for attempt in range(retries):
            try:
                login_resp = client.login(identifier=username, password=password, login_attempts=1)
                logger.info(f"Login response: {login_resp}")

                if login_resp.get('code') == 2:
                    login_resp, two_fa_message = self.handle_verify_two_fa_login(client, login_resp, twoFA_secret)

                    return login_resp, two_fa_message
                if login_resp.get('code') == 3:
                    login_resp, message = self.handle_email_verification_code(client, snapchat_account, login_resp)
                    return login_resp, message

                if login_resp.get('code') == 1:
                    return login_resp, "Login Successful"
                else:
                    return login_resp, f"Failed to login -> login response {login_resp.get('code')}. Most probably different proxy."
            except Exception as e:
                error_message = f"An error occurred during login (attempt {attempt + 1}): {str(e)}"
                logger.error(error_message)
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    return None, error_message

    def process_login_response(self, client: SnapkatClient, snapchat_account_login: SnapchatAccountLogin) -> (
            bool, str):
        """
        Processes the login response and sets up the client session.

        :param client: The Snapkat client instance.
        :param snapchat_account_login: The SnapchatAccountLogin object containing session details.
        :return: Tuple (bool, str): True if successful, False otherwise, along with a message.
        """
        try:
            # Validate that snapchat_account_login is not None
            if not snapchat_account_login:
                return False, "SnapchatAccountLogin object is None. Cannot process login response."

            # Validate that required fields are present
            required_fields = ['access_token', 'auth_token', 'user_id', 'mutable_username']
            for field in required_fields:
                if not getattr(snapchat_account_login, field, None):
                    return False, f"Missing required field '{field}' in SnapchatAccountLogin object."

            # Set client session attributes
            client.set_access_token(snapchat_account_login.access_token)
            client.set_user_auth_token(snapchat_account_login.auth_token)
            client.set_user_id(snapchat_account_login.user_id)
            client.set_mutable_username(snapchat_account_login.mutable_username)

            return True, "Login response processed successfully."
        except AttributeError as e:
            message = f"AttributeError while processing login response: {str(e)}"
            logger.error(message)
            return False, message
        except Exception as e:
            message = f"An unexpected error occurred while processing login response: {str(e)}"
            logger.error(message)
            return False, message

    def handle_fidelius_and_argos(self, client: SnapkatClient) -> (bool, str):
        """
        Handles Fidelius poll recrypt and Argos token setup with retry logic.

        :param client: The Snapkat client instance.
        :return: Tuple (bool, str): True if successful, False otherwise with an error message.
        """
        root_message = "_handle_fidelius_and_argos_"
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt} for fidelius_poll_recrypt and Argos token handling.")
                fidelius_poll_recrypt = client.fidelius_poll_recrypt()
                if fidelius_poll_recrypt:
                    logger.info(f"fidelius_poll_recrypt successful.")
                    argos_resp = client.argos_get_token()
                    client.set_argos_token(argos_resp)
                    logger.info(f"argos_token: {client.device['argos_token']['token']}")
                    return True, "Success"
                else:
                    logger.info(f"fidelius_poll_recrypt failed.")
                    return False, f"{root_message}fidelius_poll_recrypt failed"
            except Exception as e:
                error_message = str(e)
                if "Proxy Authentication Required" in error_message:
                    logger.error(f"Proxy authentication issue encountered: {error_message}")
                    wait_time = 60
                else:
                    logger.error(
                        f"An error occurred during fidelius_poll_recrypt or Argos token handling: {error_message}")
                    wait_time = 5

                if attempt < max_retries:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    final_message = f"{root_message}Maximum retry attempts reached: {error_message}"
                    logger.error(final_message)
                    return False, final_message

    def handle_email_verification_code(self, client: SnapkatClient, snapchat_account: SnapchatAccount, login_response) -> \
            Tuple[Optional[dict], str]:
        logger.info('Email verification code is required', login_response)
        odlv_data = login_response['odlv_data']
        odlv_token = odlv_data['odlv_token']
        email_hint = odlv_data['obfuscated_email']
        odlv_code_payload = {
            'odlv_preauth_token': odlv_token,
            'odlv_type': 'Email'
        }
        logger.info('Sending ODLV code to {}'.format(email_hint))
        send_odlv_response = client.send_odlv_code(odlv_code_payload)
        if 'success' in send_odlv_response:
            if not send_odlv_response['success']:
                return None,'Failed to send odlv code'
            else:
                time.sleep(90)
                logger.info('ODLV code sent to email')
                odlv_code = EmailExtractorUtils.get_code(snapchat_account.email, snapchat_account.email_password)
                odlv_code_payload['odlv_code'] = odlv_code
                logger.info('Verifying odlv code with payload', odlv_code_payload)
                verify_odlv_response = client.verify_odlv_code(odlv_code_payload)
                if verify_odlv_response['code'] != 1:
                    return None, 'Failed to verify ODLV code',
                else:
                    return verify_odlv_response, "Successfully provided odlv code"
        else:
            return None, "Failed to send ODLV code"

    def handle_verify_two_fa_login(self, client: SnapkatClient, login_response: dict, twoFA_secret: Optional[str]) -> \
            Tuple[Optional[dict], str]:
        """
        Handles two-factor authentication (2FA) login verification.

        :param client: The Snapkat client instance.
        :param login_response: The initial login response containing 2FA data.
        :param twoFA_secret: The two-factor authentication secret, if applicable.
        :return: The response from the 2FA verification attempt, or None if verification fails.
        """
        try:
            two_fa_data = SnapkatUtils.extract_two_fa_data(login_response)
            two_fa_token = two_fa_data['two_fa_token']
            otp_enabled = two_fa_data['otp_enabled']

            # Generate the 2FA code if OTP is enabled and the secret is provided
            two_fa_code = SnapkatUtils.generate_two_fa_code(twoFA_secret) if otp_enabled and twoFA_secret else None
            if not two_fa_code:
                message = "Two-factor authentication failed: OTP not enabled or secret missing."
                logger.info(message)
                return None, message

            payload = SnapkatUtils.build_two_fa_payload(two_fa_token, two_fa_code)
            verify_two_fa_response = client.verify_two_fa(payload)

            if verify_two_fa_response.get('code') == 1:
                message = "Two-factor authentication successfully verified."
                logger.info(message)
                return verify_two_fa_response, message
            else:
                message = f"Failed to verify two-factor authentication. Response: {verify_two_fa_response}"
                logger.info(message)
                return None, message

        except KeyError as e:
            message = f"Missing key in 2FA login response: {str(e)}"
            logger.error(message)
            return None, message
        except Exception as e:
            message = f"An unexpected error occurred during 2FA verification: {str(e)}"
            logger.error(message)
            return None, message

    def get_quick_adds_page(self, client: SnapkatClient, quick_adds_page: int):
        attempt = 0
        max_attempts = 2
        while attempt < max_attempts:
            try:
                # Sending Argos token because we are on quick adding
                if quick_adds_page == 0:
                    argos_resp = client.argos_get_token()
                    client.set_argos_token(argos_resp)

                # Perform quick adding
                quick_adds = client.get_quick_adds()

                if not quick_adds:
                    logger.info(f"No quick adds found on attempt {attempt + 1}.")
                else:
                    suggested_friends = quick_adds.get("suggested_friend_results_v2", [])
                    footer_friends = quick_adds.get("add_friends_footer_ordering", [])

                    # Combine suggested and footer friends based on index
                    combined_friends = [
                        {"suggested_friend": suggested_friends[i], "footer_friend": footer_friends[i]}
                        for i in range(min(len(suggested_friends), len(footer_friends)))
                    ]

                    if combined_friends:
                        return combined_friends, "Successfully retrieved quick adds"
                    else:
                        logger.info(f"No combined friends found on attempt {attempt + 1}.")

                # If execution reaches here, either quick_adds was empty or combined_friends was empty.
                attempt += 1
                if attempt < max_attempts:
                    logger.info(f"Retrying (Attempt {attempt + 1} of {max_attempts})")

            except Exception as e:
                logger.error(f"Error during quick adding requests process on attempt {attempt + 1}: {str(e)}")
                attempt += 1
                if attempt < max_attempts:
                    logger.info(
                        f"Retrying after exception... (Attempt {attempt + 1} of {max_attempts})")
                else:
                    logger.error("All retry attempts for get_quick_adds_page have failed.")
                    return None, f"Error during quick adding requests process: {str(e)}"

        # If all attempts are exhausted without success:
        message = "No quick adds found after all retry attempts."
        logger.info(message)
        return None, message

    def check_username_allow(self, username, name, user_id=None, suggestion_token=None, is_quick_add=True):
        result = SnapchatAccountValidatorService.check_username(username, name, False, user_id, suggestion_token, is_quick_add)
        allow = result.get('allow', False)
        reason = result.get('reason', '')
        return allow, reason

    def add_users(self, client, users, source='AddedBySuggested', use_argo_tokens=False):
        if use_argo_tokens:
            try:
                argos_resp = client.argos_get_token()
                client.set_argos_token(argos_resp)
            except Exception as e:
                message = f"An error occurred while getting or setting Argos token: {str(e)}"
                logger.error(message)
                return None, message

        time.sleep(1)
        page = 'add_friends_button_on_top_bar_on_camera'

        # Create user entries dynamically based on the input users list
        user_entries = []
        for user in users:
            user_entry = {
                'friend_id': user['user_id'],
                'source': source
            }
            if source == 'AddedBySuggested' and 'suggestion_token' in user:
                user_entry['suggestion_token'] = user['suggestion_token']
            user_entries.append(user_entry)

        retries = 2
        message = "Friends successfully added"
        response = None

        for attempt in range(retries):
            try:
                response = client.add_friends(page, user_entries)
                message = "Friends successfully added"
                break
            except Exception as e:
                message = f"An error occurred while adding friends (attempt {attempt + 1}): {str(e)}"
                logger.error(message)
                if attempt < retries - 1:
                    time.sleep(5)

        return response, message

    def add_user(self, client, user_id, suggestion_token='', source='AddedBySuggested'):
        try:
            # Attempt to get and set the Argos token
            argos_resp = client.argos_get_token()
            client.set_argos_token(argos_resp)
        except Exception as e:
            message = f"An error occurred while getting or setting Argos token: {str(e)}"
            logger.error(message)
            return None, message

        time.sleep(1)
        page = 'add_friends_button_on_top_bar_on_camera'

        # Create the user dictionary dynamically based on the source condition
        user_entry = {
            'friend_id': user_id,
            'source': source
        }

        # Add suggestion_token only if the source is 'AddedBySuggested'
        if source == 'AddedBySuggested':
            user_entry['suggestion_token'] = suggestion_token

        users = [user_entry]
        retries = 2
        message = "Friend successfully added"
        for attempt in range(retries):
            try:
                response = client.add_friends(page, users)
                break
            except Exception as e:
                message = f" An error occurred while adding friends (attempt {attempt + 1}): {str(e)}"
                logger.error(message)
                response = None
                if attempt < retries - 1:
                    time.sleep(5)
        return response, message

    def send_batch(self, client, batch_to_add, added_usernames, sent_requests):
        """Sends a batch of friend requests."""
        try:
            if batch_to_add:
                friend_request_sent, response_message = self.add_users(client, batch_to_add, source="AddedBySuggested")
                if friend_request_sent:
                    added_usernames.extend([user['username'] for user in batch_to_add])
                    sent_requests += len(batch_to_add)
                    logger.info(f"Batch sent: {len(batch_to_add)} friend requests. Response: {response_message}")
                    time.sleep(random.uniform(10, 25))
                else:
                    logger.info(f"Batch sent failure.")
        except Exception as e:
            logger.error(f"Failed to send batch friend requests: {str(e)}")
        batch_to_add.clear()
        return added_usernames, sent_requests

    def generate_leads_from_quick_ads(self, client, username, target_leads):
        found_leads = 0
        quick_add_pages_requested = 0
        not_allowed_count = 0
        added_usernames = []
        while found_leads < target_leads:
            quick_add_pages_requested += 1
            quick_adds, generate_leads_message = self.get_quick_adds_page(client)
            if quick_adds is None:
                message = f"When trying to generate leads , no quick adds found for user {username} on page {quick_add_pages_requested}, reason: {generate_leads_message}"
                logger.info(message)
                return found_leads, not_allowed_count, quick_add_pages_requested, message, added_usernames
            for recommendation in quick_adds:
                if found_leads >= target_leads:
                    break
                user_id = recommendation["suggested_friend"].get('userId')
                rec_username = recommendation["suggested_friend"].get('username')
                name = recommendation["suggested_friend"].get('display_name')
                suggestion_token = recommendation["footer_friend"].get('suggestion_token')
                if not user_id or not rec_username or not name:
                    continue

                allow, reason = self.check_username_allow(rec_username, name, user_id, suggestion_token, False)
                logger.info(f"Username: {rec_username}, Display Name: {name}, Allowed: {allow}, Reason: {reason}")
                if allow:
                    found_leads += 1
                    added_usernames.append(rec_username)
                else:
                    not_allowed_count += 1

        message = (
            f"Finished generating leads for user {username}. "
            f"Generated Leads: {found_leads}, Not allowed: {not_allowed_count}, "
            f"Pages requested: {quick_add_pages_requested}"
        )
        return found_leads, not_allowed_count, quick_add_pages_requested, message, added_usernames

    def process_quick_adds(self, client, username, config: QuickAdsConfig, max_friend_requests):
        sent_requests = 0
        quick_add_pages_requested = 0
        not_allowed_count = 0
        added_usernames = []
        batch_to_add = []
        for qap in range(config.max_quick_add_pages):
            quick_adds = []
            if sent_requests >= max_friend_requests:
                logger.info(f"Reached the maximum of {max_friend_requests} friend requests.")
                return sent_requests, not_allowed_count, quick_add_pages_requested, f"Reached the maximum of {max_friend_requests} friend requests.", added_usernames
            try:
                quick_adds, quick_ads_message = self.get_quick_adds_page(client, qap)
                quick_add_pages_requested += 1
                if quick_adds is None or len(quick_adds) < 10:
                    added_usernames, sent_requests = self.send_batch(client, batch_to_add, added_usernames, sent_requests)
                    if quick_adds is None:
                        message = f"No quick adds found for user {username} on page {quick_add_pages_requested}, reason: {quick_ads_message}"
                    else:
                        message = f"Quick ads on page {quick_add_pages_requested} is less or equal with 1."
                    logger.info(message)
                    params = DPARequestParams(
                        client=client,
                        quick_ads_page=qap,
                        sent_requests_quick_ads=sent_requests,
                        added_usernames=added_usernames,
                        message=message,
                        max_friend_requests=max_friend_requests,
                        users_send_in_request=config.users_sent_in_request,
                        rejected_count=not_allowed_count
                    )
                    return self.send_to_dpa_users(params)
            except Exception as e:
                logger.error(f"Error during quick adding requests process for user {username}: {str(e)}")
                continue

            for recommendation in quick_adds:
                if sent_requests >= max_friend_requests:
                    break
                user_id = recommendation["suggested_friend"].get('userId')
                rec_username = recommendation["suggested_friend"].get('username')
                name = recommendation["suggested_friend"].get('display_name')
                suggestion_token = recommendation["footer_friend"].get('suggestion_token')
                if not user_id or not rec_username or not name:
                    continue

                allow, reason = self.check_username_allow(rec_username, name, user_id, suggestion_token)
                logger.info(f"Username: {rec_username}, Display Name: {name}, Allowed: {allow}, Reason: {reason}")
                if allow:
                    batch_to_add.append({
                        'user_id': user_id,
                        'username': rec_username,
                        'display_name': name,
                        'suggestion_token': suggestion_token
                    })
                    if len(batch_to_add) + sent_requests > max_friend_requests:
                        remaining_slots = max_friend_requests - sent_requests
                        batch_to_add = batch_to_add[:remaining_slots]

                    if len(batch_to_add) >= config.users_sent_in_request or sent_requests + len(
                            batch_to_add) >= max_friend_requests:
                        added_usernames, sent_requests = self.send_batch(client, batch_to_add, added_usernames,
                                                                         sent_requests)
                else:
                    not_allowed_count += 1
                    logger.info(f"User {rec_username} (Name: {name}) is not allowed. Reason: {reason}")

        added_usernames, sent_requests = self.send_batch(client, batch_to_add, added_usernames, sent_requests)
        logger.info(
            f"Finished processing quick adds for user {username}. Sent requests: {sent_requests}, Not allowed: {not_allowed_count}, Pages requested: {quick_add_pages_requested}")
        return sent_requests, not_allowed_count, quick_add_pages_requested, f"Finished processing quick adds for user {username}. Sent requests: {sent_requests}, Not allowed: {not_allowed_count}, Pages requested: {quick_add_pages_requested}", added_usernames

    def process_consume_leads(self, client, username, config: ConsumeLeadsConfig, max_friend_requests):
        sent_requests = 0
        added_usernames = []
        batch_to_add = []
        message = ""
        leads_response = SnapchatAccountValidatorService.get_leads(max_friend_requests)
        if "error" in leads_response:
            message = f"Error while retrieving leads: {leads_response['error']}"
            logger.error(message)
            return sent_requests, added_usernames, message, False
        elif not leads_response:
            message = "No leads found to consume."
            logger.error(message)
            return sent_requests, added_usernames, message, False
        else:
            for lead in leads_response:
                batch_to_add.append({
                    'user_id': lead["user_id"],
                    'username': lead["username"],
                    'suggestion_token': lead["suggestion_token"]
                })
                if len(batch_to_add) + sent_requests > max_friend_requests:
                    remaining_slots = max_friend_requests - sent_requests
                    batch_to_add = batch_to_add[:remaining_slots]

                if len(batch_to_add) >= config.users_sent_in_request or sent_requests + len(
                        batch_to_add) >= max_friend_requests:
                    added_usernames, sent_requests = self.send_batch(client, batch_to_add, added_usernames,
                                                                     sent_requests)
            enough_leads = True if len(leads_response) == max_friend_requests else False
            added_usernames, sent_requests = self.send_batch(client, batch_to_add, added_usernames, sent_requests)
            if enough_leads:
                message = f"Sent requests: {sent_requests}."
            else:
                message = f"Sent requests: {sent_requests}. Not enough leads were retrieved"
            logger.info(message)
            return sent_requests, added_usernames, message, enough_leads


    def process_quick_adds_batch(
            self,
            snapchat_account: SnapchatAccount,
            config: QuickAdsConfig
    ) -> QuickAddsResult:
        """
        Processes batches of quick adds for a given Snapchat account.

        :param snapchat_account: The Snapchat account to process.
        :param account_execution_id: ID for tracking execution.
        :param max_starting_delay: Initial delay before starting the process.
        :param requests: Total friend requests to send.
        :param batches: Number of batches to divide requests into.
        :param batch_delay: Delay between batches.
        :return: QuickAddsResult object with process details.
        """
        # Start with a delay
        time.sleep(random.uniform(0, config.max_starting_delay))
        # Initialize statistics
        total_sent_requests = 0
        total_rejected_count = 0
        total_quick_add_pages_requested = 0
        message = ""
        added_users = []
        try:
            # # Create and log in the client
            client, result_message = self.create_and_login_client(snapchat_account)
            if not client:
                message = (f"[Worker-{config.account_execution_id}] Failed to create and login Snapkat client "
                           f"for record {snapchat_account.id}. Debug message: {result_message}")
                logger.info(message)
                return QuickAddsResult(
                    total_sent_requests=0,
                    rejected_count=0,
                    quick_add_pages_requested=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            username = snapchat_account.username
            if not username:
                message = (f"[Worker-{config.account_execution_id}] Missing username for record "
                           f"{snapchat_account.id}.")
                logger.info(message)
                return QuickAddsResult(
                    total_sent_requests=0,
                    rejected_count=0,
                    quick_add_pages_requested=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            # Process batches
            batch_no = 1
            for _ in range(config.batches):
                batch_size = config.requests // config.batches
                sent_requests, rejected_count, quick_add_pages_requested, stop_reason, added_usernames = self.process_quick_adds(
                    client=client,
                    username=username,
                    config=config,
                    max_friend_requests=batch_size
                )

                # Update statistics
                total_sent_requests += sent_requests
                total_rejected_count += rejected_count
                total_quick_add_pages_requested += quick_add_pages_requested
                added_users.extend(added_usernames)

                # Update batch message
                message += f"Batch {batch_no}: {stop_reason}\n"

                # Increment batch count and add delay
                batch_no += 1
                time.sleep(config.batch_delay)

            logger.info(
                f"[Account Execution-{config.account_execution_id}] Total friend requests sent: {total_sent_requests} for user {username}")
            logger.info(
                f"[Account Execution-{config.account_execution_id}] Total users rejected: {total_rejected_count} for user {username}")
            logger.info(
                f"[Account Execution-{config.account_execution_id}] Total quick add pages requested: {total_quick_add_pages_requested} for user {username}")

            # Return result
            return QuickAddsResult(
                total_sent_requests=total_sent_requests,
                rejected_count=total_rejected_count,
                quick_add_pages_requested=total_quick_add_pages_requested,
                added_users=added_users,
                success=True,
                message=message.strip()  # Remove trailing newline
            )
        except Exception as e:
            message = f"Exception caught during quick ads: {e}"
            logger.error(message)
            return QuickAddsResult(
                total_sent_requests=0,
                rejected_count=0,
                quick_add_pages_requested=0,
                added_users=[],
                success=False,
                message=message
            )

    def update_record_device(self, snapchat_account: SnapchatAccount, device_json: str):
        """
        Updates or creates a Device record associated with a Snapchat account.

        :param snapchat_account: SnapchatAccount object to associate the device with
        :param device_json: JSON string representing the device data
        """
        device = Device(
            data=device_json,
            snapchat_account_id=snapchat_account.id
        )

        snapchat_account.device = device

    def process_get_conversations(
            self,
            snapchat_account: SnapchatAccount,
            account_execution_id: int,
            max_starting_delay: int,
    ) -> CheckConversationsResult:
        """
        Processes retrieval of conversations for a given Snapchat account.

        :param snapchat_account: The Snapchat account to process.
        :param account_execution_id: ID for tracking execution.
        :param max_starting_delay: Initial delay before starting the process.
        :return: CheckConversationsResult object with process details.
        """
        # Start with a random delay
        time.sleep(random.uniform(0, max_starting_delay))

        # Initialize statistics
        conversations_count = 0

        # Create and log in the client
        client, result_message = self.create_and_login_client(snapchat_account)
        if not client:
            message = (
                f"[Worker-{account_execution_id}] Failed to create and login Snapkat client "
                f"for record {snapchat_account.id}. Debug message: {result_message}"
            )
            logger.info(message)
            return CheckConversationsResult(
                conversations=0,
                latest_events=[],
                success=False,
                message=message,
            )

        username = snapchat_account.username
        if not username:
            message = (
                f"[Worker-{account_execution_id}] Missing username for record "
                f"{snapchat_account.id}."
            )
            logger.info(message)
            return CheckConversationsResult(
                conversations=0,
                latest_events=[],
                success=False,
                message=message,
            )

        # Prepare payload and query conversations
        payload = {
            "sender_user_id": client.device["user_id"],
            "count": 100000,
        }
        try:
            resp = client.query_conversations(payload)
            conversations = resp.get("conversations", [])
            conversations_count = len(conversations)

            # Extract latest events
            latest_events: List[str] = []
            for conv in conversations:
                epoch_time = conv.get("last_event_timestamp")
                if epoch_time:
                    epoch_time_seconds = epoch_time / 1000
                    utc_time = datetime.fromtimestamp(epoch_time_seconds, timezone.utc).isoformat()
                    latest_events.append(utc_time)

            # Return successful result
            return CheckConversationsResult(
                conversations=conversations_count,
                latest_events=latest_events,
                success=True,
                message="Conversations retrieved successfully",
            )
        except Exception as e:
            message = (
                f"[Worker-{account_execution_id}] Error retrieving conversations: {str(e)}"
            )
            logger.info(message)
            return CheckConversationsResult(
                conversations=0,
                latest_events=[],
                success=False,
                message=message,
            )

    def process_send_to_user(
            self,
            snapchat_account: SnapchatAccount,
            account_execution_id: int,
            max_starting_delay: int,
            username: str
    ) -> SendToUsernameResult:
        """
        Processes retrieval of conversations for a given Snapchat account.

        :param snapchat_account: The Snapchat account to process.
        :param account_execution_id: ID for tracking execution.
        :param max_starting_delay: Initial delay before starting the process.
        :return: CheckConversationsResult object with process details.
        """
        # Start with a random delay
        time.sleep(random.uniform(0, max_starting_delay))

        # Create and log in the client
        client, result_message = self.create_and_login_client(snapchat_account)
        if not client:
            message = (
                f"[Worker-{account_execution_id}] Failed to create and login Snapkat client "
                f"for record {snapchat_account.id}. Debug message: {result_message}"
            )
            logger.info(message)
            return SendToUsernameResult(
                success=False,
                message=message,
            )

        account_username = snapchat_account.username
        if not account_username:
            message = (
                f"[Worker-{account_execution_id}] Missing username for record "
                f"{snapchat_account.id}."
            )
            logger.info(message)
            return SendToUsernameResult(
                success=False,
                message=message,
            )

        return self.send_to_username(client, username, account_execution_id)

    def process_check_status(
            self,
            snapchat_account: SnapchatAccount,
            account_execution_id: int,
            max_starting_delay: int,
    ) -> CheckStatusResult:
        """
        Processes checking the status for a given Snapchat account.

        :param snapchat_account: The Snapchat account to process.
        :param account_execution_id: ID for tracking execution.
        :param max_starting_delay: Initial delay before starting the process.
        :return: Boolean indicating if the account is valid.
        """
        # Start with a random delay
        time.sleep(random.uniform(0, max_starting_delay))

        try:
            # Start with a random delay
            delay = random.uniform(0, max_starting_delay)
            logger.info(f"Delaying {account_execution_id} execution by {delay:.2f} seconds...")
            time.sleep(delay)

            # Construct the URL to check the account status
            url = f"https://www.snapchat.com/add/{snapchat_account.username}"
            logger.info(f"Checking account status for: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            url = f"https://www.snapchat.com/add/{snapchat_account.username}"
            response = requests.get(url, headers=headers)

            # Check the response status code
            if response.status_code == 200:
                message = f"Account {snapchat_account.username} is still valid"
                return CheckStatusResult(
                    success=True,
                    message=message
                )
            elif response.status_code == 404:
                message = f"Account validation for {snapchat_account.username} likely failed because the account no longer exists. Response status code: {response.status_code}"
                return CheckStatusResult(
                    success=False,
                    message=message
                )
            else:
                message = f"Account validation for {snapchat_account.username} failed but not with account not found. Response status code: {response.status_code}"
                return CheckStatusResult(
                    success=False,
                    message=message
                )

        except requests.RequestException as e:
            message = f"An error occurred while checking the account: {e}"
            return CheckStatusResult(
                success=False,
                message=message
            )

    def send_to_username(self, client, username, account_execution_id) -> SendToUsernameResult:
        try:
            device = client.device
            payload = SnapkatUtils.construct_search_payload(device, username)
            search_result = client.search(payload)
            user_id_to_add, message = SnapkatUtils.extract_user_id(search_result, username, account_execution_id)
            if not user_id_to_add:
                message = (
                    f"[Worker-{account_execution_id}] User with username {username} could not be found."
                )
                logger.info(message)
                return SendToUsernameResult(
                    success=False,
                    message=message,
                )
            users_to_add = [{'user_id': user_id_to_add, 'suggestion_token': ''}]
            response, response_message = self.add_users(client, users_to_add, source='AddedBySearch')
            if not response:
                logger.info(response_message)
                return SendToUsernameResult(
                    success=False,
                    message=response_message,
                )

            return SendToUsernameResult(
                success=True,
                message=f"Friend request successfully sent to user {username}.",
            )
        except Exception as e:
            message = (
                f"[Worker-{account_execution_id}] Error sending add request: {str(e)}"
            )
            logger.info(message)
            return SendToUsernameResult(
                success=False,
                message=message,
            )

    def generate_leads(
            self,
            snapchat_account: SnapchatAccount,
            account_execution_id: int,
            target_leads: int
    ) -> GenerateLeadsResult:
        try:
            # # Create and log in the client
            client, result_message = self.create_and_login_client(snapchat_account)
            if not client:
                message = (f"[Worker-{account_execution_id}] Failed to create and login Snapkat client "
                           f"for record {snapchat_account.id}. Debug message: {result_message}")
                logger.info(message)
                return GenerateLeadsResult(
                    generated_leads=0,
                    rejected_count=0,
                    quick_add_pages_requested=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            username = snapchat_account.username
            if not username:
                message = (f"[Worker-{account_execution_id}] Missing username for record "
                           f"{snapchat_account.id}.")
                logger.info(message)
                return GenerateLeadsResult(
                    generated_leads=0,
                    rejected_count=0,
                    quick_add_pages_requested=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            found_leads, not_allowed_count, quick_add_pages_requested, message, added_usernames = self.generate_leads_from_quick_ads(
                client=client,
                username=username,
                target_leads=target_leads,
            )

            logger.info(
                f"[Account Execution-{account_execution_id}] Total found leads: {found_leads} for user {username}")
            logger.info(
                f"[Account Execution-{account_execution_id}] Total users rejected: {not_allowed_count} for user {username}")
            logger.info(
                f"[Account Execution-{account_execution_id}] Total quick add pages requested: {quick_add_pages_requested} for user {username}")

            # Return result
            return GenerateLeadsResult(
                generated_leads=found_leads,
                rejected_count=not_allowed_count,
                quick_add_pages_requested=quick_add_pages_requested,
                added_users=added_usernames,
                success=True,
                message=message.strip()  # Remove trailing newline
            )
        except Exception as e:
            message = f"Exception caught during generate leads: {e}"
            logger.error(message)
            return GenerateLeadsResult(
                generated_leads=0,
                rejected_count=0,
                quick_add_pages_requested=0,
                added_users=[],
                success=False,
                message=message
            )

    def process_set_bitmoji(self, snapchat_account: SnapchatAccount, start_delay: int, account_execution_id: int):
        time.sleep(random.uniform(0, start_delay))
        try:
            # # Create and log in the client
            client, result_message = self.create_and_login_client(snapchat_account)
            if not client:
                message = (f"[Worker-{account_execution_id}] Failed to create and login Snapkat client "
                           f"for record {snapchat_account.id}. Debug message: {result_message}")
                logger.info(message)
                return CheckStatusResult(
                    success=False,
                    message=message
                )

            username = snapchat_account.username
            if not username:
                message = (f"[Worker-{account_execution_id}] Missing username for record "
                           f"{snapchat_account.id}.")
                logger.info(message)
                return CheckStatusResult(
                    success=False,
                    message=message
                )

            resp, msg = client.set_bitmoji()
            return CheckStatusResult(
                success=True,
                message=msg,
            )
        except Exception as e:
            message = f"Exception caught consume leads: {e}"
            logger.error(message)
            return CheckStatusResult(
                success=False,
                message=message
            )

    def process_change_bitmoji(self, snapchat_account: SnapchatAccount, start_delay: int, account_execution_id: int):
        time.sleep(random.uniform(0, start_delay))
        try:
            # # Create and log in the client
            client, result_message = self.create_and_login_client(snapchat_account)
            if not client:
                message = (f"[Worker-{account_execution_id}] Failed to create and login Snapkat client "
                           f"for record {snapchat_account.id}. Debug message: {result_message}")
                logger.info(message)
                return CheckStatusResult(
                    success=False,
                    message=message
                )

            username = snapchat_account.username
            if not username:
                message = (f"[Worker-{account_execution_id}] Missing username for record "
                           f"{snapchat_account.id}.")
                logger.info(message)
                return CheckStatusResult(
                    success=False,
                    message=message
                )
            result = client.unlink_bitmoji()

            if result == False:
                return CheckStatusResult(
                    success=False,
                    message="Failed to unlinked bitmoji",
                )

            resp, msg = client.set_bitmoji()
            return CheckStatusResult(
                success=True,
                message=msg,
            )
        except Exception as e:
            message = f"Exception caught consume leads: {e}"
            logger.error(message)
            return CheckStatusResult(
                success=False,
                message=message
            )

    def process_consume_leads_batch(
            self,
            snapchat_account: SnapchatAccount,
            config: ConsumeLeadsConfig
    ) -> ConsumeLeadsResult:
        """
        Processes batches of consume leads for a given Snapchat account.

        :param snapchat_account: The Snapchat account to process.
        :param account_execution_id: ID for tracking execution.
        :param max_starting_delay: Initial delay before starting the process.
        :param requests: Total friend requests to send.
        :param batches: Number of batches to divide requests into.
        :param batch_delay: Delay between batches.
        :return: ConsumeLeadsResult object with process details.
        """
        # Start with a delay
        time.sleep(random.uniform(0, config.max_starting_delay))
        # Initialize statistics
        total_sent_requests = 0
        message = ""
        added_users = []
        result_success = True
        try:
            # # Create and log in the client
            client, result_message = self.create_and_login_client(snapchat_account)
            if not client:
                message = (f"[Worker-{config.account_execution_id}] Failed to create and login Snapkat client "
                           f"for record {snapchat_account.id}. Debug message: {result_message}")
                logger.info(message)
                return ConsumeLeadsResult(
                    total_sent_requests=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            username = snapchat_account.username
            if not username:
                message = (f"[Worker-{config.account_execution_id}] Missing username for record "
                           f"{snapchat_account.id}.")
                logger.info(message)
                return ConsumeLeadsResult(
                    total_sent_requests=0,
                    added_users=[],
                    success=False,
                    message=message
                )

            # Process batches
            batch_no = 1
            for _ in range(config.batches):
                batch_size = config.requests // config.batches
                sent_requests, added_usernames, message, enough_leads = self.process_consume_leads(
                    client=client,
                    username=username,
                    config=config,
                    max_friend_requests=batch_size
                )

                # Update statistics
                total_sent_requests += sent_requests
                added_users.extend(added_usernames)

                # Update batch message
                message += f"Batch {batch_no}: {message}\n"
                result_success = enough_leads
                if not enough_leads:
                    break
                # Increment batch count and add delay
                batch_no += 1
                time.sleep(config.batch_delay)

            logger.info(
                f"[Account Execution-{config.account_execution_id}] Total friend requests sent: {total_sent_requests} for user {username}")

            # Return result
            return ConsumeLeadsResult(
                total_sent_requests=total_sent_requests,
                added_users=added_users,
                success=result_success,
                message=message.strip()  # Remove trailing newline
            )
        except Exception as e:
            message = f"Exception caught consume leads: {e}"
            logger.error(message)
            return ConsumeLeadsResult(
                total_sent_requests=0,
                added_users=[],
                success=False,
                message=message
            )

    def send_to_dpa_users(self, params: DPARequestParams):
        """
        Sends friend requests to users from the DPA (Direct People Ads) system.

        :param params: An instance of DPARequestParams containing all required parameters.

        :return: Tuple (total sent requests, 0, 0, status message, updated added_usernames).
        """
        retries = 3
        root_message = ""
        users_to_send = min(10, params.max_friend_requests - params.sent_requests_quick_ads)
        reason_message = params.message if params.message else f"No additional quick ads pages found after page {params.quick_ads_page}."

        if params.quick_ads_page >= 1:
            root_message = (
                f"{reason_message} Already sent requests to {params.sent_requests_quick_ads} users. "
                f"Attempting to send requests to up to {users_to_send} more users from DPA."
            )
        else:
            root_message = f"{reason_message}. Attempting to send requests to up to {users_to_send} more users from DPA."

        sent_requests = 0
        batch_to_add = []

        for attempt in range(retries):
            try:
                users = SnapchatAccountValidatorService.get_users(users_to_send)

                if not users or "error" in users:
                    logger.info(f"Attempt {attempt + 1}: No users retrieved from DPA.")
                    message = f"Attempt {attempt + 1}: No users retrieved from DPA."
                    continue  # Retry if no users were fetched

                for user in users:
                    batch_to_add.append(user)

                    if len(batch_to_add) >= params.users_send_in_request or params.sent_requests_quick_ads + len(
                            batch_to_add) >= users_to_send:
                        params.added_usernames, params.sent_requests_quick_ads = self.send_batch(
                            params.client, batch_to_add, params.added_usernames, params.sent_requests_quick_ads
                        )

                params.added_usernames, params.sent_requests_quick_ads = self.send_batch(
                    params.client, batch_to_add, params.added_usernames, params.sent_requests_quick_ads
                )
                return (
                        params.sent_requests_quick_ads, params.rejected_count, params.quick_ads_page,
                        f"{root_message} Requests sent to users from DPA.",
                        params.added_usernames
                )
            except requests.RequestException as e:
                logger.error(f"Attempt {attempt + 1}: Error occurred while making the request: {e}")
                message = f"Attempt {attempt + 1}: Error occurred while making the request: {e}"

        return (
            sent_requests + params.sent_requests_quick_ads, params.rejected_count, params.quick_ads_page,
            f"{root_message}, Failed to send to users from DPA: {message}",
            params.added_usernames
        )
