import base64
import secrets
import struct
import gzip
import binascii
import re
import uuid
from typing import Optional, Dict

import pyotp
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.schemas.proxy import Proxy


class SnapkatUtils:
    URL_PATTERN = r'(https?://[^\s]+)'

    @staticmethod
    def write_request_frame(message: bytes) -> bytes:
        header_bytes = struct.pack('>I', len(message))
        status_code = bytes([0])
        header_bytes = status_code + header_bytes
        return header_bytes + message

    @staticmethod
    def read_request_frame(resp: bytes, gzip_compressed: bool = False) -> bytes:
        return gzip.decompress(resp[5:]) if gzip_compressed else resp[5:]

    @staticmethod
    def decrypt_snap(key: str, iv: str, encrypted_data: bytes) -> bytes:
        key = base64.b64decode(key)
        iv = base64.b64decode(iv)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(decrypted_data) + unpadder.finalize()

    @staticmethod
    def encrypt_snap(plaintext_data: bytes, key: str = None, iv: str = None) -> dict:
        if key and iv:
            key = base64.b64decode(key)
            iv = base64.b64decode(iv)

        if not key:
            key = secrets.token_bytes(32)

        if not iv:
            iv = secrets.token_bytes(16)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext_data) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        return {
            'encrypted_data': encrypted_data,
            'media_encryption_data': {
                'key': base64.b64encode(key).decode(),
                'iv': base64.b64encode(iv).decode(),
            }
        }

    @staticmethod
    def parse_conversation_versions(conversations_sync_response: dict) -> list:
        conversation_versions = []
        for conv in conversations_sync_response['conversations']:
            conversation_info = conv['conversation_info']
            conversation_id = SnapkatUtils.decode_uuid(bytearray(conversation_info['conversation_id']['id']))
            conversation_version = conversation_info['conversation_version']
            conversation_versions.append({
                'conversation_id': conversation_id,
                'conversation_version': conversation_version
            })
        return conversation_versions

    @staticmethod
    def parse_incoming_friend_reqs(friends_response: dict) -> list:
        friends = friends_response['friends']
        friend_ids = [f['user_id'] for f in friends]
        incoming_friend_requests = []

        for friend in friends_response['added_friends']:
            if friend['user_id'] not in friend_ids:
                incoming_friend_requests.append(friend)
        return incoming_friend_requests

    @staticmethod
    def parse_uuid(high_bits: int, low_bits: int) -> str:
        mask = 0xFFFFFFFFFFFFFFFF
        high_bits_unsigned = high_bits & mask
        low_bits_unsigned = low_bits & mask
        merged_uuid = (high_bits_unsigned << 64) | low_bits_unsigned
        return str(uuid.UUID(int=merged_uuid))

    @staticmethod
    def decode_uuid(bytes_: bytes) -> str:
        uuid_hex = binascii.hexlify(bytes_).decode('ascii')
        return f"{uuid_hex[:8]}-{uuid_hex[8:12]}-{uuid_hex[12:16]}-{uuid_hex[16:20]}-{uuid_hex[20:]}"

    @staticmethod
    def encode_uuid(uuid_str: str) -> bytes:
        uuid_hex = uuid_str.replace("-", "")
        return binascii.unhexlify(uuid_hex)

    @staticmethod
    def find_urls_indices(text: str) -> list:
        urls_found = []
        for match in re.finditer(SnapkatUtils.URL_PATTERN, text):
            start_index = match.start()
            end_index = match.end() - 1
            url = match.group()
            urls_found.append((start_index, end_index, url))
        return urls_found

    @staticmethod
    def build_two_fa_payload(two_fa_token: str, two_fa_code: str) -> dict:
        """
        Builds the payload for the 2FA verification request.

        :param two_fa_token: The two-factor authentication token.
        :param two_fa_code: The generated two-factor authentication code.
        :return: A dictionary representing the payload for the 2FA verification.
        """
        payload = {
            "two_fa_token": two_fa_token,
            "two_fa_code": two_fa_code,
            "two_fa_type": "OTP",  # Can be SMS if using SMS-based 2FA
            "remember_device": False,  # Change to True to remember this device
        }
        print(f"Built 2FA payload: {payload}")
        return payload

    @staticmethod
    def generate_two_fa_code(twoFA_secret: str) -> str:
        """
        Generates a two-factor authentication code using TOTP.

        :param twoFA_secret: The two-factor authentication secret.
        :return: A generated TOTP code as a string.
        """
        sanitized_secret = twoFA_secret.replace(" ", "")
        totp = pyotp.TOTP(sanitized_secret)
        two_fa_code = totp.now()
        print(f"Generated 2FA code using TOTP: {two_fa_code}")
        return two_fa_code

    @staticmethod
    def extract_two_fa_data(login_response: dict) -> dict:
        """
        Extracts two-factor authentication data from the login response.

        :param login_response: The initial login response.
        :return: A dictionary containing two-factor authentication data.
        """
        print("Processing 2FA login response:", login_response)
        two_fa_data = login_response.get('two_fa_data', {})
        print("Extracted 2FA data:", two_fa_data)
        return two_fa_data

    @staticmethod
    def configure_proxies(proxy: Proxy) -> Optional[Dict[str, str]]:
        """
        Configure proxy settings based on the fields.

        :param fields: A dictionary containing proxy configuration fields.
        :return: A dictionary containing HTTP and HTTPS proxy URLs, or None if no proxy is configured.
        """
        proxy_host: Optional[str] = proxy.host
        proxy_port: Optional[str] = proxy.port
        proxy_username: Optional[str] = proxy.proxy_username
        proxy_password: Optional[str] = proxy.proxy_password

        if not proxy_host:
            return None

        proxy_auth: str = f"{proxy_username}:{proxy_password}@" if proxy_username and proxy_password else ""
        proxy_url: str = f"http://{proxy_auth}{proxy_host}:{proxy_port}"
        print(f"Using proxy: {proxy_url}")

        return {
            'http://': proxy_url,
            'https://': proxy_url
        }

    @staticmethod
    def extract_user_id(search_result: dict, username: str, execution_id: int) -> Optional[tuple]:
        """
        Extracts the user ID from the search result.

        :param search_result: The result of the search request.
        :param username: Username that was searched for.
        :param execution_id: ID for tracking execution.
        :return: User ID if found, None otherwise.
        """
        try:
            return search_result["sections"][0]["results"][0]["result"]["User"]["id"], "Id retrieved successfully"
        except (IndexError, KeyError):
            log_message = f"[Worker-{execution_id}] Failed to extract user ID for username: {username}"
            print(log_message)
            return None, log_message

    @staticmethod
    def construct_search_payload(device: dict, username: str) -> dict:
        """
        Constructs the payload for the search request.

        :param device: Device information from the client.
        :param username: Username to search for.
        :return: Dictionary payload for the search request.
        """
        return {
            "query_string": username,
            "origin": "OriginCamera",
            "request_options": {},
            "session_id": str(uuid.uuid4()),
            "session_query_id": "0",
            "user_info": {
                "age": 24,
                "country_code": device["device_region"],
                "bitmoji_avatar_id": "",
                "astrological_sign": "Cancer",
                "timezone": device["timezone"]
            }
        }