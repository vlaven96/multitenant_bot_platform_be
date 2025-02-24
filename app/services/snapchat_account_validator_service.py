from datetime import datetime
from app.database import SessionLocal
from app.schemas.snapchat_checked_accounts.snapchat_allowed_user import SnapchatAllowedUser
from app.schemas.snapchat_checked_accounts.snapchat_rejected_user import SnapchatRejectedUser
import random
import logging
from bs4 import BeautifulSoup
from openai import OpenAI
import requests
from sqlalchemy import asc

from app.utils.proxy_generator import ProxyGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SnapchatAccountValidatorService:
    OPEN_ROUTER_KEY = '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'
    DEEPINFRA_KEY = 'oLpemCz911mkV92R2FtqQMRwxtJbNgXf'

    OPEN_ROUTER_CLIENT = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPEN_ROUTER_KEY
    )
    DEEPINFRA_ROUTER_CLIENT = OpenAI(
        base_url="https://api.deepinfra.com/v1/openai",
        api_key=DEEPINFRA_KEY
    )

    @staticmethod
    def check_username(username: str,
                       name: str,
                       allow_duplicates: bool = False,
                       user_id: str = None,
                       suggestion_token: str = None, is_quick_add = True) -> dict:
        """
        Checks the validity of a username and name based on predefined rules.

        :param username: The username to validate.
        :param name: The name associated with the username.
        :param allow_duplicates: Whether duplicate usernames are allowed.
        :return: A dictionary containing `allow` (bool) and `reason` (str).
        """
        logger.info(f"Validating username: {username}, name: {name}, allow_duplicates: {allow_duplicates}")
        try:
            with SessionLocal() as db:
                # Check if the username is in bad_usernames cache
                cached_bad = db.query(SnapchatRejectedUser).filter_by(username=username).first()
                if cached_bad:
                    logger.info(f"Username found in bad_usernames: {username} - rejecting")
                    return {"allow": False, "reason": cached_bad.reason}

                # Check if the username already exists
                if not allow_duplicates:
                    existing_user = db.query(SnapchatAllowedUser).filter_by(username=username).first()
                    if existing_user:
                        if existing_user.request_count > 0:
                            reason = "Username already exists"
                            logger.info(f"Username already exists: {username} - rejecting")
                            if existing_user.user_id == None:
                                existing_user.user_id = user_id
                                db.add(existing_user)
                                db.commit()
                            return {"allow": False, "reason": reason}
                        else:
                            existing_user.request_count = 1
                            existing_user.user_id = user_id
                            db.add(existing_user)
                            db.commit()
                            return {"allow": True, "reason": "Username is acceptable"}


                # Check if the name is English
                if not SnapchatAccountValidatorService.is_english(name):
                    reason = "Name is not English"
                    logger.info(f"Name is not English - rejecting. Username: {username}, Name: {name}")
                    SnapchatAccountValidatorService.add_to_bad_usernames(username, reason)
                    return {"allow": False, "reason": reason}

                # Check Bitmoji
                bitmoji_check = SnapchatAccountValidatorService.check_bitmoji(username)
                if not bitmoji_check["allow"]:
                    reason = bitmoji_check["reason"]
                    logger.info(f"Bitmoji check failed - rejecting. Username: {username}, Reason: {reason}")
                    if "Error while retrieving image" not in reason:
                        SnapchatAccountValidatorService.add_to_bad_usernames(username, reason)
                    return {"allow": False, "reason": reason}

                # Username is acceptable
                logger.info(f"Good username - accepting: {username}, name: {name}")
                existing_user = db.query(SnapchatAllowedUser).filter_by(username=username).first()
                if not existing_user:
                    request_count = 1 if is_quick_add else 0
                    new_user = SnapchatAllowedUser(
                        username=username,
                        name=name,
                        last_requested_at=datetime.utcnow(),
                        request_count=request_count,
                        user_id=user_id,
                        suggestion_token=suggestion_token
                    )
                    db.add(new_user)
                    db.commit()

                return {"allow": True, "reason": "Username is acceptable"}
        except Exception as e:
            logger.error(f"Error while validating username: {username}. Error: {e}")
            return {"allow": False, "reason": "An internal error occurred"}

    @staticmethod
    def add_to_bad_usernames(username: str, reason: str):
        """
        Adds a username to the bad_usernames table with a given reason.

        :param username: The username to add.
        :param reason: The reason for rejection.
        """
        try:
            with SessionLocal() as db:
                if not db.query(SnapchatRejectedUser).filter_by(username=username).first():
                    bad_user = SnapchatRejectedUser(username=username, reason=reason)
                    db.add(bad_user)
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to add username to bad_usernames: {username}. Error: {e}")

    @staticmethod
    def is_english(name: str) -> bool:
        """
        Checks if a name is in English using external APIs.

        :param name: The name to check.
        :return: True if the name is in English, False otherwise.
        """
        try:
            rand_val = random.random()
            if rand_val < 0.5:
                client = SnapchatAccountValidatorService.OPEN_ROUTER_CLIENT
                model_name = "meta-llama/llama-3.1-70b-instruct"
            else:
                client = SnapchatAccountValidatorService.DEEPINFRA_ROUTER_CLIENT
                model_name = "meta-llama/Meta-Llama-3.1-70B-Instruct"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze this name of the user: '{name}'. Classify if the user is living in the United States. "
                                   "Reply no if any of the names aren't English. Ignore Emojis. Reply only with yes or no."
                    }
                ],
                temperature=0.0,
                max_tokens=1,
            )
            reply = response.choices[0].message.content.strip().lower()
            return reply == "yes" or reply == "yes."
        except Exception as e:
            logger.error(f"Error checking if name is English: {name}. Error: {e}")
            return False

    @staticmethod
    def get_username_from_title(title):
        at_index = title.find('@')
        word_after_at = title[at_index + 1:].split()[0]
        return word_after_at[:-1]

    @staticmethod
    def get_bitmoji_image_url(username: str):
        generated_proxy = ProxyGenerator.generate_proxy()
        proxy = {
            "http": generated_proxy,
            "https": generated_proxy
        }
        url = f"https://www.snapchat.com/add/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        try:
            response = requests.get(url, proxies=proxy, headers=headers, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            username_from_page = SnapchatAccountValidatorService.get_username_from_title(title_tag.get_text())

            if username_from_page != username:
                username = username_from_page
                url = f"https://www.snapchat.com/add/{username}"
                response = requests.get(url, proxies=proxy, headers=headers, allow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            img_tag = soup.find('img', alt=f"3D Bitmoji for {username}")

            # Public Profile
            if not img_tag:
                img_tag = soup.find('img', alt="Profile Picture")
                if img_tag and 'srcset' in img_tag.attrs:
                    return img_tag['srcset'], "Successfully retrieved image"

            if img_tag and 'srcset' in img_tag.attrs:
                source_tag = soup.find('source', {'type': 'image/webp'})
                if source_tag and 'srcset' in source_tag.attrs:
                    return source_tag['srcset'] + "&scale=0&trim=circle", "Successfully retrieved image"
                else:
                    return img_tag['srcset'], "Successfully retrieved image"
            return None, "Public profile or no profile"

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None, f"Error while retrieving image: {e}"

    @staticmethod
    def check_image(image_url: str):
        for _ in range(2):
            response = SnapchatAccountValidatorService.OPEN_ROUTER_CLIENT.chat.completions.create(
                model="meta-llama/llama-3.2-11b-vision-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What is the tone of the skin of the character in this image? What is the gender of the character? Reply short"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=50
            )
            content = response.choices[0].message.content.strip().lower() if response.choices else ""
            print("API response content:", content)
            if content != "the character in the image appears to be a female, as indicated by the long hair and pink color. the tone of the skin is light pink.":
                break
        if not content:
            return {"allow": False, "reason": "Error processing bitmoji, maybe doesn't exist"}
        elif 'brown' in content and 'light' not in content:
            return {"allow": False, "reason": "Bitmoji has brown skin"}
        elif 'black' in content or 'dark' in content:
            return {"allow": False, "reason": "Bitmoji has black skin"}
        elif 'female' in content:
            return {"allow": False, "reason": "Bitmoji has female character"}
        elif 'male' not in content and 'man' not in content:
            return {"allow": True, "reason": "Nobody in the picture"}
        else:
            return {"allow": True}

    @staticmethod
    def check_image_age(image_url):
        for _ in range(2):
            response = SnapchatAccountValidatorService.OPEN_ROUTER_CLIENT.chat.completions.create(
                model="amazon/nova-lite-v1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What is the approximate age of the person in this cartoon-style avatar? Reply with just a number and nothing else."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=50
            )
            content = response.choices[0].message.content.strip().lower()
            if content:
                break

        try:
            # Extract the first number from the response
            age = int(''.join(filter(str.isdigit, content)))
            if age < 20:
                return {"allow": False, "reason": f"Bitmoji appears to be {age} years old (too young)", "image": image_url}
            return {"allow": True, "reason": f"Bitmoji appears to be {age} years old", "image": image_url}
        except (ValueError, TypeError):
            return {"allow": True, "reason": "Could not determine age of bitmoji", "image": image_url}

    @staticmethod
    def check_bitmoji(username: str) -> dict:
        image_url, message = SnapchatAccountValidatorService.get_bitmoji_image_url(username)
        if image_url is None:
            return {"allow": False, "reason": message}
        else:
            result = SnapchatAccountValidatorService.check_image(image_url)
            if not result["allow"]:
                return result
            return SnapchatAccountValidatorService.check_image_age(image_url)

    @staticmethod
    def get_usernames(num_usernames: int, model_id: str = None) -> dict:
        """
        Retrieves a specified number of usernames from the database, optionally filtered by model_id,
        ordered by the last time requested.

        :param num_usernames: The number of usernames to retrieve.
        :param model_id: (Optional) The model_id to filter usernames by.
        :return: A dictionary containing a list of usernames or an error message.
        """
        logger.info(f"Request received to fetch {num_usernames} usernames with model_id={model_id}.")
        try:
            with SessionLocal() as db:
                query = db.query(SnapchatAllowedUser).order_by(SnapchatAllowedUser.last_requested_at)

                # Apply model_id filter if provided
                if model_id:
                    query = query.filter(SnapchatAllowedUser.model_id == model_id)

                # Fetch the specified number of usernames
                usernames = query.limit(num_usernames).all()

                # Update last_time_requested and number_of_times_requested
                today = datetime.utcnow()
                for user in usernames:
                    user.last_requested_at = today
                    user.request_count += 1
                db.commit()

                # Return the usernames
                return {"usernames": [user.username for user in usernames]}
        except Exception as e:
            logger.error(f"Error fetching usernames: {e}")
            return {"error": "Failed to retrieve usernames"}

    @staticmethod
    def get_users(num_users: int, model_id: str = None) -> list:
        """
        Retrieves a specified number of usernames from the database, optionally filtered by model_id,
        ordered by the last time requested.

        :param num_users: The number of users to retrieve.
        :param model_id: (Optional) The model_id to filter usernames by.
        :return: A dictionary containing a list of usernames or an error message.
        """
        logger.info(f"Request received to fetch {num_users} users with model_id={model_id}.")
        try:
            with SessionLocal() as db:
                query = (
                    db.query(SnapchatAllowedUser)
                    .filter(SnapchatAllowedUser.user_id != None)
                    .order_by(SnapchatAllowedUser.last_requested_at)
                )

                # Apply model_id filter if provided
                if model_id:
                    query = query.filter(SnapchatAllowedUser.model_id == model_id)

                # Fetch the specified number of usernames
                users = query.limit(num_users).all()
                user_dicts = []
                # Update last_time_requested and number_of_times_requested
                today = datetime.utcnow()
                for user in users:
                    user.last_requested_at = today
                    user.request_count += 1

                    user_dicts.append({
                        "user_id": user.user_id,
                        "username": user.username,
                        "display_name": user.name,
                        "suggestion_token": user.suggestion_token
                    })
                db.commit()

                # Return the usernames
                return user_dicts
        except Exception as e:
            logger.error(f"Error fetching usernames: {e}")
            return {"error": "Failed to retrieve usernames"}

    @staticmethod
    def get_leads(num_usernames: int, model_id: str = None) -> dict:
        """
        Retrieves a specified number of usernames from the database, optionally filtered by model_id,
        ordered by the last time requested.

        :param num_usernames: The number of usernames to retrieve.
        :param model_id: (Optional) The model_id to filter usernames by.
        :return: A list of dictionaries with user_id and suggestion_token.
        """
        logger.info(f"Request received to fetch {num_usernames} usernames with model_id={model_id}.")
        try:
            with SessionLocal() as db:
                query = db.query(SnapchatAllowedUser)

                if model_id:
                    query = query.filter(SnapchatAllowedUser.model_id == model_id)

                # Apply additional filters and order
                query = (
                    query.filter(SnapchatAllowedUser.user_id.isnot(None))
                    .filter(SnapchatAllowedUser.request_count < 1)
                    .order_by(asc(SnapchatAllowedUser.last_requested_at))
                    .limit(num_usernames)
                )

                leads = query.limit(num_usernames).all()

                today = datetime.utcnow()
                for user in leads:
                    user.last_requested_at = today
                    user.request_count += 1
                db.commit()

                # Return the usernames
                return [{"user_id": user.user_id, "suggestion_token": user.suggestion_token, "username": user.username} for user in leads]
        except Exception as e:
            logger.error(f"Error fetching usernames: {e}")
            return {"error": f"Failed to retrieve leads: {e}"}