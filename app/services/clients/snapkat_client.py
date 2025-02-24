import base64
import json
import uuid
import random
from typing import Dict, Any

from google.protobuf.json_format import ParseDict

from app.models.exception_models.snapkat_api_error import SnapkatApiError, SnapkatHttpError
from app.models.request_action import RequestAction
from app.services.clients.snapchat_client import SnapchatClient
from app.utils.decoders.argo_token_decoder import ArgosTokenDecoder
from app.utils.encoders.send_friend_encoder import FriendActionEncoder
from app.utils.http_request_handler import HttpRequestHandler
from app.utils.loggig_manager import LoggingManager
from app.utils.snapkat_utils import SnapkatUtils
from app.protos import snapkat_pb2
import requests
import time
import logging

logger = logging.getLogger(__name__)

class SnapkatClient():
    """
    http/https proxy:
    {
        'http': 'http://ip:port',
        'https': 'http://ip:port'
    }
    """
    BASE_URL = "https://snapkat.cc"

    # Snapkat Endpoints
    DEVICE_TEMPLATE = f"{BASE_URL}/device/get_device_template"
    SIGN_SC_ATTESTATION = f"{BASE_URL}/sign/sc-attestation"
    SIGN_SC_ATTESTATION_TOKEN = f"{BASE_URL}/sign/sc-attestation-token"
    PROTO = f"{BASE_URL}/proto"
    SIGN_REQUEST = f"{BASE_URL}/request/sign"
    DECODE_REQUEST = f"{BASE_URL}/request/decode"

    # Snapchat Endpoints
    GET_FRIENDS = "https://us-east4-gcp.api.snapchat.com/ami/friends"
    GET_QUICK_ADDS = "https://us-east4-gcp.api.snapchat.com/suggest_friend_high_availability"
    SEARCH_PRE_TYPE = "https://aws.api.snapchat.com/search/pretype"
    SEARCH = "https://aws.api.snapchat.com/search/search"
    BITMOJI_SET = "https://us-east1-aws.api.snapchat.com/bitmoji-api/avatar-service/create-avatar-data"

    def __init__(self, snapkat_api_key: str, proxies: dict = {}):
        self.api_key = snapkat_api_key
        self.snapkat_headers = {'content-type': 'application/json', 'x-snapkat-key': self.api_key}
        self.device = {}
        self.proxies = proxies
        self.cof_bin_ids = 'CMXMbwjelrIBCIqXuwEIoqC4AQjj2MIBCPqL5gE'
        self.setup()
        self.x_snapchat_att_token = None
        self.http_handler: HttpRequestHandler = LoggingManager.get_instance().http_handler

    def setup(self):
        self.snapchat = SnapchatClient(self.proxies)

    def test_proxy(self):
        self.snapchat.test_proxy()

    def set_device(self, device: dict):
        self.device = device

    def convert_device_to_proto(self, ref):
        device_copy = self.device.copy()
        device_copy['user_agent'] = device_copy['user-agent']
        del device_copy['user-agent']
        device_copy['grpc_user_agent'] = device_copy['grpc-user-agent']
        del device_copy['grpc-user-agent']
        device_copy['x_snap_access_token'] = device_copy['x-snap-access-token']
        del device_copy['x-snap-access-token']
        ParseDict(device_copy, ref)

    def get_encoded_self_user_id(self) -> bytes:
        if 'user_id' in self.device and self.device['user_id']:
            return SnapkatUtils.encode_uuid(self.device['user_id'])
        else:
            print("user_id does not exist in device object or is empty")
            exit(1)

    def set_access_token(self, token: str):
        self.device['x-snap-access-token'] = token

    def set_user_auth_token(self, token: str):
        self.device['user_auth_token'] = token

    def set_user_id(self, user_id: str):
        self.device["user_id"] = user_id

    def set_mutable_username(self, username: str):
        self.device["mutable_username"] = username

    def set_argos_token(self, argos_resp):
        token = base64.b64encode(bytes(argos_resp['token1']['argos_token']['token'])).decode()
        security_clearance = argos_resp['token1']['argos_token']['security_clearance']
        self.device['argos_token'] = {'token': token, 'security_clearance': security_clearance}

    def add_friends(self, page: str, users: list):
        payload = {'page': page, 'users': users}
        if self.x_snapchat_att_token!=None:
            snap_token = self.x_snapchat_att_token
        else:
            snap_token = self.get_x_snapchat_att_token()
            self.x_snapchat_att_token = snap_token
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "x-snapchat-argos-strict-enforcement": "true",
            "x-snapchat-att-token": snap_token['x-snapchat-att-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.AddFriends, payload, extra_headers=extra)

    def remove_friends(self, users: list):
        payload = {'user_ids': users}
        snap_token = self.get_x_snapchat_att_token()
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "x-snapchat-argos-strict-enforcement": "true",
            "x-snapchat-att-token": snap_token['x-snapchat-att-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.RemoveFriends, payload, extra_headers=extra)

    def get_self_avatar(self, payload={}):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.GetSelfAvatar, payload, extra_headers=extra)

    def get_friends_userscore(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.GetFriendsUserScore, payload, extra_headers=extra)

    def get_user_id_by_username(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.DeepLinkRequest, payload, extra, True)

    def get_snapchatters_public_info(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token'],
            "accept-language": self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.GetSnapchattersPublicInfo, payload, extra)

    def get_friends(self, added_friends_sync_token="", friends_sync_token=""):
        headers = self.get_form_headers(with_auth=True)
        friends_request_payload = {
            "added_friends_sync_token": added_friends_sync_token,
            "friends_sync_token": friends_sync_token,
        }
        payload = {
            "friends_request": json.dumps(friends_request_payload)
        }
        # resp = requests.post(self.GET_FRIENDS, headers=headers, data=payload, proxies=self.proxies)
        resp = self.requests_with_retry("POST", self.GET_FRIENDS, headers=headers, data=payload,
                                        proxies=self.proxies)
        return resp.json()

    def batch_delta_sync(self, payload):
        extra = {
            'mcs-cof-ids-bin': self.cof_bin_ids,
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.BatchDeltaSync, payload, extra_headers=extra)

    def delta_sync(self, payload):
        extra = {
            # 'mcs-cof-ids-bin': self.cof_bin_ids,
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.DeltaSync, payload, extra_headers=extra)

    def upload_media(self, upload_url: str, binary_data: bytes):
        return self.snapchat.upload_media(upload_url, self.device, binary_data, {})

    def search_pretype(self, payload: dict):
        request_payload = self.encode_proto_request('Search', payload)
        headers = self.get_proto_headers(with_auth=True)
        # snap_response = requests.post(self.SEARCH_PRE_TYPE, headers=headers, data=request_payload, proxies=self.proxies)
        snap_response = self.requests_with_retry("POST", self.SEARCH_PRE_TYPE, headers=headers, data=request_payload,
                                        proxies=self.proxies)
        snap_response_content = snap_response.content
        return self.decode_request_response(snapkat_pb2.SnapkatDecodeResponseType.DECODE_SEARCH_RESPONSE,
                                            snap_response_content)

    def search(self, payload: dict):
        signed_request = self.sign_request(RequestAction.Search, payload).json()
        headers = self.get_form_headers(with_auth=True)
        # snap_response = requests.post(self.SEARCH, headers=headers, data=bytearray(signed_request['request_payload']),
        #                               proxies=self.proxies)
        snap_response = self.requests_with_retry("POST", self.SEARCH, headers=headers, data=bytearray(signed_request['request_payload']), proxies=self.proxies)
        snap_response_content = snap_response.content
        return self.decode_request_response(12, snap_response_content, True)

    def sync_conversations(self, payload):
        extra = {
            'mcs-cof-ids-bin': self.cof_bin_ids,
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.SyncConversations, payload, extra_headers=extra)

    def create_content_message(self, payload):
        extra = {
            'mcs-cof-ids-bin': self.cof_bin_ids,
            'x-snap-access-token': self.device['x-snap-access-token'],
            'x-snap-route-tag': '',
        }
        return self.make_snapkat_request(RequestAction.CreateContentMessage, payload, extra_headers=extra)

    def write_binary_resp(self, name: str, data: bytes):
        with open(name, 'wb') as f:
            f.write(data)
            f.close()

    def save_device(self, name: str):
        self.write_json_resp(name, self.device)

    def write_json_resp(self, name: str, data: dict):
        with open(name, 'w+') as f:
            f.write(json.dumps(data))
            f.close()

    def send_odlv_code(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.SendODLVCode, payload, extra_headers=extra)

    def check_username(self, payload, allow_recycled_username=True):
        extra = {
            "allow-recycled-username": "true" if allow_recycled_username else "false",
        }
        return self.make_snapkat_request(RequestAction.CheckUsername, payload, extra_headers=extra)

    def get_quick_adds(self, action="list", last_sync_timestamp=0):
        if self.x_snapchat_att_token!=None:
            snap_token = self.x_snapchat_att_token
        else:
            snap_token = self.get_x_snapchat_att_token()
            self.x_snapchat_att_token = snap_token
        headers = self.get_form_headers(with_auth=True)
        headers.update({
            "x-snapchat-argos-strict-enforcement": "true",
            "x-snapchat-att-token": snap_token['x-snapchat-att-token'],
            "x-request-id": headers['x-snapchat-uuid']
        })
        payload = {
            'action': action,
            'last_sync_timestamp': last_sync_timestamp
        }
        # resp = requests.post(self.GET_QUICK_ADDS, headers=headers, data=payload, proxies=self.proxies)
        resp = self.requests_with_retry("POST", self.GET_QUICK_ADDS, headers=headers, data=payload, proxies=self.proxies)
        return resp.json()

    def send_typing_notification(self, payload):
        extra = {
            'mcs-cof-ids-bin': self.cof_bin_ids,
            'x-snap-access-token': self.device['x-snap-access-token']
        }
        return self.make_snapkat_request(RequestAction.SendTypingNotification, payload, extra_headers=extra)

    def set_display_name(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.SetDisplayName, payload, extra_headers=extra)

    def change_username(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
            "allow-recycled-username": "true"
        }
        return self.make_snapkat_request(RequestAction.ChangeUsername, payload, extra_headers=extra,
                                         with_x_snapchat_att=True)

    def sc_reauth(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.ScReAuth, payload, extra_headers=extra)

    def update_email(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.UpdateEmail, payload, extra_headers=extra)

    def verify_challenge(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.VerifyChallenge, payload, extra_headers=extra)

    def query_conversations(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.QueryConversations, payload, extra_headers=extra)

    def update_content_message(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.UpdateContentMessage, payload, extra_headers=extra)

    def query_messages(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.QueryMessages, payload, extra_headers=extra)

    def verify_odlv_code(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.VerifyODLVCode, payload, extra_headers=extra)

    def verify_two_fa(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.VerifyTwoFA, payload, extra_headers=extra)

    def discover_stories(self, payload={}):
        extra = {
            'accept-language': self.device['device_language'],
        }
        return self.make_snapkat_request(RequestAction.GetStories, payload, extra_headers=extra)

    def update_conversation(self, payload):
        extra = {
            'accept-language': self.device['device_language'],
            'x-snap-access-token': self.device['x-snap-access-token'],
        }
        return self.make_snapkat_request(RequestAction.UpdateConversation, payload, extra_headers=extra)

    def get_upload_locations_by_key_request(self, payload):
        extra = {
            'x-snap-access-token': self.device['x-snap-access-token'],
            'x-snap-route-tag': '',
        }
        return self.make_snapkat_request(RequestAction.GetUploadLocationsByKey, payload, extra_headers=extra)

    def argos_get_token(self):
        extra = {
            'x-snap-access-token': self.device['x-snap-access-token'],
            'x-snap-route-tag': '',
        }
        return self.make_snapkat_request(RequestAction.ArgosGetToken, {}, extra_headers=extra)

    def fidelius_poll_recrypt(self):
        extra = {
            'x-snap-access-token': self.device['x-snap-access-token']
        }
        return self.make_snapkat_request(RequestAction.FideliusPollRecrypt, {}, extra_headers=extra)

    def sync_custom_story_groups(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token']
        }
        return self.make_snapkat_request(RequestAction.SyncCustomStoryGroups, payload, extra_headers=extra)

    def delete_custom_story(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token']
        }
        return self.make_snapkat_request(RequestAction.DeleteCustomStoryGroup, payload, extra_headers=extra)

    def create_custom_story(self, payload):
        extra = {
            "x-snap-access-token": self.device['x-snap-access-token']
        }
        return self.make_snapkat_request(RequestAction.CreateCustomStoryGroup, payload, extra_headers=extra)

    def login(self, password: str, identifier: str = "", email: str = "", phone_number: str = "", login_attempts=0):
        payload = {
            "identifier": {},
            "password": password,
            "source": "UsernamePasswordPage",
            "login_attempts": login_attempts
        }

        if identifier:
            payload["identifier"] = {"Username": identifier}
        elif email:
            payload["identifier"] = {"Email": email}
        elif phone_number:
            payload["identifier"] = {"PhoneNumber": phone_number}

        return self.make_snapkat_request(RequestAction.LoginWithPassword, payload)

    def make_snapkat_request(
            self,
            action: RequestAction,
            payload: dict,
            extra_headers: dict = {},
            with_x_snapchat_att=False,
            with_auth=True,
            with_timestamp=False,
    ):
        signed_request_response = None
        if action == RequestAction.AddFriends:
            signed_request_response = FriendActionEncoder.encode_request(payload)
        else:
            try:
                signed_request = self.sign_request(action, payload)
            except requests.RequestException as e:
                logger.error(f"HTTP request failed during signing: {e}")
                raise SnapkatHttpError(500, f"Request failed during signing: {e}")

            if signed_request.status_code != 200:
                logger.error(
                    f"Signing request failed. Status: {signed_request.status_code}, Response: {signed_request.text}")
                raise SnapkatHttpError(signed_request.status_code, signed_request.text)

            signed_request_response = signed_request.json()
            if 'error_code' in signed_request_response:
                raise SnapkatApiError(signed_request_response['error_code'],
                                      f"Failed to sign Snapkat gRPC request for action {action.value}, Error Data: \"{signed_request_response['message']}\"")

        additional_request_headers = signed_request_response['additional_request_headers']
        request_url = signed_request_response['request_url']

        if with_x_snapchat_att:
            if not additional_request_headers:
                additional_request_headers = {}
            x_snapchat_att = self.get_x_snapchat_att(request_url)
            additional_request_headers.update(x_snapchat_att)

        request_payload = self.snapchat.compute_final_request_payload(signed_request_info=signed_request_response)
        snapchat_response = None
        try:
            snapchat_response = self.snapchat.make_snapchat_request(
                request_url,
                self.device,
                request_payload,
                extra_headers,
                signed_request_response,
                with_timestamp,
                with_auth
            )
        except requests.RequestException as e:
            logger.error(f"HTTP request to Snapchat failed: {e}")
            raise SnapkatHttpError(500, f"Snapchat request failed: {e}")

        response_content_type = signed_request_response['response_content_type']
        action_decode_type = action.to_decode_type()

        if action_decode_type > 0:
            if action_decode_type == 999 and response_content_type not in ['FORM', 'JSON']:
                # return true if the request to snapchat's server was successful
                # since in this case, the particular request does not have any response body
                return snapchat_response['status'] <= 204
            else:
                if response_content_type in ["GRPC", "PROTO", "BINARY"]:
                    return self.decode_request_response(action_decode_type, snapchat_response['respBody'],
                                                        action.should_include_device())
                elif response_content_type == "JSON":
                    return json.loads(snapchat_response['respBody'])
                elif response_content_type in ["FORM"]:  # figure out wtf to do with this
                    return snapchat_response['respBody']
        else:
            return snapchat_response['status'] <= 204

    def set_bitmoji(self):
        snap_token = self.get_x_snapchat_att_token()
        headers = self.get_form_headers(with_auth=True)
        headers.update({
            "x-snapchat-argos-strict-enforcement": "true",
            "x-snapchat-att-token": snap_token['x-snapchat-att-token'],
            "x-request-id": headers['x-snapchat-uuid']
        })

        # Select random bitmoji
        bitmoji_data = [
            "CP///////////wESoQkIAhAFGhAKCXNraW5fdG9uZRCI2cYHGg8KCWhhaXJfdG9uZRCevHwaCQoEaGFpchD3FhoICgNqYXcQ/woaCQoEYnJvdxCmDBoICgNleWUQ0wwaCgoFcHVwaWwQ6BAaEQoKcHVwaWxfdG9uZRC11+UBGgkKBG5vc2UQ0wsaCgoFbW91dGgQpRIaCAoDZWFyEJYLGggKBGJvZHkQBxoTCg9mYWNlX3Byb3BvcnRpb24QARoMCgdleWVsYXNoEOkRGhEKDWNsb3RoaW5nX3R5cGUQARoICgNoYXQQwUMaEAoJaGF0X3RvbmUxEJ2OyAYaEAoJaGF0X3RvbmUyEJ2OyAYaEAoJaGF0X3RvbmUzEJ2OyAYaEAoJaGF0X3RvbmU0EJ2OyAYaEAoJaGF0X3RvbmU1EJ2OyAYaEAoJaGF0X3RvbmU2EJ2OyAYaEAoJaGF0X3RvbmU3EJ2OyAYaEAoJaGF0X3RvbmU4EJ2OyAYaEAoJaGF0X3RvbmU5EJ2OyAYaCAoDdG9wEJUHGgsKBmJvdHRvbRCaBxoNCghmb290d2VhchCYBxoJCgRzb2NrEKcCGhAKCXRvcF90b25lMRDP8fsHGhAKCXRvcF90b25lMhDP8fsHGhAKCXRvcF90b25lMxDP8fsHGhAKCXRvcF90b25lNBDP8fsHGhAKCXRvcF90b25lNRD69esHGhAKCXRvcF90b25lNhCA+fEDGhAKCXRvcF90b25lNxD69esHGhAKCXRvcF90b25lOBCKob8GGhAKCXRvcF90b25lORDx2rUDGhEKCnRvcF90b25lMTAQ+fz9AxoTCgxib3R0b21fdG9uZTEQ2PnuBBoTCgxib3R0b21fdG9uZTIQ5abBBxoSCgxib3R0b21fdG9uZTMQ0aYtGhMKDGJvdHRvbV90b25lNBDt1dsHGhMKDGJvdHRvbV90b25lNRDo4PUBGhMKDGJvdHRvbV90b25lNhCWpeYEGhMKDGJvdHRvbV90b25lNxDt1dsHGhMKDGJvdHRvbV90b25lOBCEvc0BGhMKDGJvdHRvbV90b25lORDRgOECGhQKDWJvdHRvbV90b25lMTAQvYnHBhoVCg5mb290d2Vhcl90b25lMRC7i7cHGhUKDmZvb3R3ZWFyX3RvbmUyEJvBtgYaFQoOZm9vdHdlYXJfdG9uZTMQu4u3BxoVCg5mb290d2Vhcl90b25lNBC7i7cHGhUKDmZvb3R3ZWFyX3RvbmU1EN3r+wcaFQoOZm9vdHdlYXJfdG9uZTYQg93mBhoVCg5mb290d2Vhcl90b25lNxDd6/sHGhUKDmZvb3R3ZWFyX3RvbmU4EKrHsgYaFQoOZm9vdHdlYXJfdG9uZTkQu4u3BxoWCg9mb290d2Vhcl90b25lMTAQzoDKBRoRCgpzb2NrX3RvbmUxEOvhzwcaEQoKc29ja190b25lMhDTiOEBGhEKCnNvY2tfdG9uZTMQ6+HPBxoRCgpzb2NrX3RvbmU0EOvhzwcaDQoJaXNfdHVja2VkEAEaFQoOZXllc2hhZG93X3RvbmUQqPm1BxoRCgpibHVzaF90b25lEKDdxQc=",
            "CP///////////wESvAcIAhAFGhAKCXNraW5fdG9uZRCI2cYHGhAKCWhhaXJfdG9uZRC6gtUCGgkKBGhhaXIQxBcaCAoDamF3EP8KGgkKBGJyb3cQpgwaCAoDZXllENAMGgoKBXB1cGlsEOgQGhEKCnB1cGlsX3RvbmUQtdflARoJCgRub3NlENMLGgoKBW1vdXRoEKQSGggKA2VhchCWCxoICgRib2R5EAkaEwoPZmFjZV9wcm9wb3J0aW9uEAEaDAoHZXllbGFzaBDpERoICgN0b3AQoQYaCwoGYm90dG9tEKsFGg0KCGZvb3R3ZWFyEPEGGhEKDWNsb3RoaW5nX3R5cGUQARoVChFub3NlcmluZ19ub3N0cmlsTBAbGh4KF25vc2VyaW5nX25vc3RyaWxMX3RvbmUxEIWY/wcaHgoXbm9zZXJpbmdfbm9zdHJpbExfdG9uZTIQhZj/BxoQCgl0b3BfdG9uZTEQq9GdAxoQCgl0b3BfdG9uZTIQ79nDBxoQCgl0b3BfdG9uZTMQ4MjxAxoQCgl0b3BfdG9uZTQQ0KfvBhoQCgl0b3BfdG9uZTUQ4LiJAxoQCgl0b3BfdG9uZTYQh82WBhoQCgl0b3BfdG9uZTcQ/v37BxoQCgl0b3BfdG9uZTgQ+8eGBRoQCgl0b3BfdG9uZTkQuOTMARoRCgp0b3BfdG9uZTEwEO/ZwwcaEwoMYm90dG9tX3RvbmUxENv6xAEaEwoMYm90dG9tX3RvbmUyENv6xAEaEwoMYm90dG9tX3RvbmUzENv6xAEaEwoMYm90dG9tX3RvbmU0ENv6xAEaEwoMYm90dG9tX3RvbmU1EOGd7wUaEwoMYm90dG9tX3RvbmU2ENyIvgYaEwoMYm90dG9tX3RvbmU3EM3oqAEaEwoMYm90dG9tX3RvbmU4EK2k3QQaEwoMYm90dG9tX3RvbmU5EIn9ugcaFAoNYm90dG9tX3RvbmUxMBCj684GGhUKDmZvb3R3ZWFyX3RvbmUxEPr16wcaFQoOZm9vdHdlYXJfdG9uZTIQ1q3bBhoUCg5mb290d2Vhcl90b25lMxCXrlwaFQoOZm9vdHdlYXJfdG9uZTQQ+vXrBxoVCg5mb290d2Vhcl90b25lNRDh3ccHGhUKDmZvb3R3ZWFyX3RvbmU2EPr16wcaFQoOZm9vdHdlYXJfdG9uZTcQ+vXrBxoVCg5mb290d2Vhcl90b25lOBCr2uYGGhUKDmZvb3R3ZWFyX3RvbmU5EPr16wcaFQoPZm9vdHdlYXJfdG9uZTEwEJeuXA==",
            "CP///////////wEStAsIAhAFGhAKCXNraW5fdG9uZRCG4/oHGhAKCWhhaXJfdG9uZRD9kL8HGgkKBGhhaXIQqAoaCAoDamF3EP8KGgkKBGJyb3cQpgwaCAoDZXllENQMGgoKBXB1cGlsEOgQGhEKCnB1cGlsX3RvbmUQtdflARoJCgRub3NlENMLGgoKBW1vdXRoEKQSGggKA2VhchCWCxoICgRib2R5EAcaEwoPZmFjZV9wcm9wb3J0aW9uEAEaDAoHZXllbGFzaBDpERoRCg1jbG90aGluZ190eXBlEAEaGgoTaGFpcl90cmVhdG1lbnRfdG9uZRCl8uwCGhIKDmVhcnJpbmdSX2xvYmUxEAYaGwoUZWFycmluZ1JfbG9iZTFfdG9uZTEQhZj/BxobChRlYXJyaW5nUl9sb2JlMV90b25lMhCFmP8HGhsKFGVhcnJpbmdSX2xvYmUxX3RvbmUzEIWY/wcaGwoUZWFycmluZ1JfbG9iZTFfdG9uZTQQhZj/BxoSCg5lYXJyaW5nTF9sb2JlMRAGGhsKFGVhcnJpbmdMX2xvYmUxX3RvbmUxEIWY/wcaGwoUZWFycmluZ0xfbG9iZTFfdG9uZTIQhZj/BxobChRlYXJyaW5nTF9sb2JlMV90b25lMxCFmP8HGhsKFGVhcnJpbmdMX2xvYmUxX3RvbmU0EIWY/wcaEgoNY2hlZWtfZGV0YWlscxD0DBoICgNoYXQQ10MaEAoJaGF0X3RvbmUxELPmzAEaEAoJaGF0X3RvbmUyELPmzAEaEAoJaGF0X3RvbmUzELPmzAEaEAoJaGF0X3RvbmU0ELPmzAEaEAoJaGF0X3RvbmU1ELPmzAEaEAoJaGF0X3RvbmU2ELPmzAEaEAoJaGF0X3RvbmU3ELPmzAEaEAoJaGF0X3RvbmU4ELPmzAEaEAoJaGF0X3RvbmU5ELPmzAEaCAoDdG9wEP4BGgsKBmJvdHRvbRC0BxoNCghmb290d2VhchD1ARoJCgRzb2NrEKcCGhAKCXRvcF90b25lMRDzwfcFGhAKCXRvcF90b25lMhDzwfcFGhAKCXRvcF90b25lMxDzwfcFGhAKCXRvcF90b25lNBDzwfcFGhAKCXRvcF90b25lNRD54fsGGhAKCXRvcF90b25lNhCjx44FGhAKCXRvcF90b25lNxD877sHGhAKCXRvcF90b25lOBDmj78EGhAKCXRvcF90b25lORDA8MwBGhEKCnRvcF90b25lMTAQgPPJAxoTCgxib3R0b21fdG9uZTEQjZuuBBoTCgxib3R0b21fdG9uZTIQjZuuBBoTCgxib3R0b21fdG9uZTMQjZuuBBoTCgxib3R0b21fdG9uZTQQjZuuBBoTCgxib3R0b21fdG9uZTUQ3LjlAhoTCgxib3R0b21fdG9uZTYQo8eOBRoTCgxib3R0b21fdG9uZTcQw4ePBhoTCgxib3R0b21fdG9uZTgQ3LTJAhoTCgxib3R0b21fdG9uZTkQnsCEARoUCg1ib3R0b21fdG9uZTEwEMWLkwYaFAoOZm9vdHdlYXJfdG9uZTEQnLRsGhQKDmZvb3R3ZWFyX3RvbmUyEJWoUBoUCg5mb290d2Vhcl90b25lMxCctGwaFAoOZm9vdHdlYXJfdG9uZTQQnLRsGhUKDmZvb3R3ZWFyX3RvbmU1EKjOoAEaFQoOZm9vdHdlYXJfdG9uZTYQ7dStAxoVCg5mb290d2Vhcl90b25lNxCozqABGhUKDmZvb3R3ZWFyX3RvbmU4EKHChAEaFQoOZm9vdHdlYXJfdG9uZTkQocKEARoVCg9mb290d2Vhcl90b25lMTAQlKBIGhEKCnNvY2tfdG9uZTEQ6+HPBxoRCgpzb2NrX3RvbmUyENOI4QEaEQoKc29ja190b25lMxDr4c8HGhEKCnNvY2tfdG9uZTQQ6+HPBxoNCglpc190dWNrZWQQAQ=="
        ]
        payload = random.choice(bitmoji_data)
        try:
            resp = self.requests_with_retry("POST", self.BITMOJI_SET, headers=headers,
                                            data=bytes(base64.b64decode(payload)), proxies=self.proxies)
            message = f"Bitmoji set response status: {resp.status_code}"
            logger.info(message)
            return resp, message
        except Exception as e:
            message = f"Error setting bitmoji: {str(e)}"
            logger.error(message)
            return None, message

    def sign_request(self, action: RequestAction, payload: dict):
        json_data = {
            "device": self.device,
            "payload": {
                action.value: payload,
            },
        }
        return self.http_handler.make_request(method="POST",
                                              url=self.SIGN_REQUEST,
                                              headers=self.snapkat_headers,
                                              json=json_data,
                                              timeout=30
                                              )
        # return requests.post(self.SIGN_REQUEST, headers=self.snapkat_headers, json=json_data, timeout=30)

    def decode_request_response(self, decode_type, resp, should_include_device):
        payload = snapkat_pb2.SnapkatDecodeProtoPayload()
        payload.type = decode_type
        payload.payload_bytes = resp
        if should_include_device:
            self.convert_device_to_proto(payload.device)
        decoded_resp_json = None
        if decode_type == 2:
            decoded_resp_json = ArgosTokenDecoder.decode_argos_protobuf_response(payload.SerializeToString())
        else:
            decoded_resp = self.http_handler.make_request(method="POST",
                                                          url=self.DECODE_REQUEST,
                                                          headers={'x-snapkat-key': self.api_key,
                                                                   'content-type': 'application/octet-stream'},
                                                          data=payload.SerializeToString()
                                                          )
            decoded_resp_json = decoded_resp.json()

        if 'error_code' in decoded_resp_json:
            raise SnapkatApiError(decoded_resp_json['error_code'],
                                  f"Failed to decode response body for type {decode_type}, Error Data: \"{decoded_resp_json['message']}\"")

        return decoded_resp_json

    def get_form_headers(self, with_auth=False):
        req_id = str(uuid.uuid4()).upper()
        request_headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=utf-8',
            'user-agent': self.device['user-agent'],
            'accept': 'application/json',
            'x-snapchat-uuid': req_id,
            'x-request-id': req_id,
            'accept-language': self.device['device_language'],
        }

        if with_auth:
            request_headers['x-snap-access-token'] = self.device['x-snap-access-token']

        return request_headers

    def get_device_template(self, device_model_name=''):
        params = {'device_model_name': device_model_name}
        device_template_req = self.http_handler.make_request(method="GET",
                                                             url=self.DEVICE_TEMPLATE,
                                                             params=params,
                                                headers=self.snapkat_headers)
        # device_template_req = requests.get(self.DEVICE_TEMPLATE, params=params,
        #                                    headers=self.snapkat_headers)
        device_template_resp = device_template_req.json()
        if 'error_code' in device_template_resp:
            raise SnapkatApiError(device_template_resp['error_code'],
                                  f"Failed to retrieve device template, Error Data: \"{device_template_resp['message']}\"")
        return device_template_resp

    def get_x_snapchat_att_token(self):
        sc_attestation_token_req = self.http_handler.make_request(method="POST",
                                                                  url=self.SIGN_SC_ATTESTATION_TOKEN,
                                                                  json={'device': self.device},
                                                                  headers=self.snapkat_headers)
        # sc_attestation_token_req = requests.post(self.SIGN_SC_ATTESTATION_TOKEN,
        #                                          json={'device': self.device},
        #                                          headers=self.snapkat_headers)
        sc_attestation_token_resp = sc_attestation_token_req.json()
        if 'error_code' in sc_attestation_token_resp:
            raise SnapkatApiError(sc_attestation_token_resp['error_code'],
                                  f"Failed to sign SC attestation token, Error Data: \"{sc_attestation_token_resp['message']}\"")
        return sc_attestation_token_resp

    def get_x_snapchat_att(self, url):
        x_snapchat_att_req = self.http_handler.make_request(method="POST",
                                               url=self.SIGN_SC_ATTESTATION,
                                               json={'device': self.device, 'url': url},
                                               headers=self.snapkat_headers
                                               )
        # x_snapchat_att_req = requests.post(self.SIGN_SC_ATTESTATION,
        #                                    json={'device': self.device, 'url': url},
        #                                    headers=self.snapkat_headers)
        x_snapchat_att_resp = x_snapchat_att_req.json()
        if 'error_code' in x_snapchat_att_resp:
            raise SnapkatApiError(x_snapchat_att_resp['error_code'],
                                  f"Failed to sign SC attestation, Error Data: \"{x_snapchat_att_resp['message']}\"")
        return x_snapchat_att_resp

    def requests_with_retry(self, method, url, **kwargs):
        """
        Makes an HTTP request using `requests` with retry logic for all HTTP methods.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST', 'PUT', etc.).
            url (str): The URL to make the request to.
            retries (int): Number of retry attempts (default: 3).
            backoff_factor (float): Factor for exponential backoff (default: 2.0).
            **kwargs: Additional arguments for `requests.request`.

        Returns:
            requests.Response: The response object from the server.
            If all retries fail, returns a dummy `requests.Response` with status code 500.
        """
        last_response = None  # Store the last response or None if no response is received
        retries = 6
        backoff_factor = 10.0

        for attempt in range(retries):
            try:
                response = requests.request(method, url, **kwargs)
                last_response = response  # Save the last response

                # Check for proxy issue (407) or request timeout (408)
                if response.status_code in (407, 408):
                    status = response.status_code
                    logger.warning(f"Issue detected on attempt {attempt + 1}: HTTP {status}")
                    if attempt < retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.info(f"Retrying in {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                        continue  # Retry the request
                    else:
                        logger.error(f"All retries for HTTP {status} issues have failed.")
                return response  # Return the response if successful

            except requests.exceptions.Timeout as e:
                # Specific handling for timeouts
                logger.warning(f"Attempt {attempt + 1} timed out: {e}")
                if attempt < retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time:.1f} seconds after timeout...")
                    time.sleep(wait_time)
                else:
                    logger.error("All retries for timeout errors have failed.")

            except requests.exceptions.RequestException as e:
                # Handling for all other request-related exceptions
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    # Exponential backoff
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("All retries for request exceptions have failed.")

        # Return the last response or a fallback response with status 500
        if last_response:
            logger.info(f"Returning the last response with status code: {last_response.status_code}")
            return last_response
        else:
            # Create a dummy response with error details
            dummy_response = requests.Response()
            dummy_response.status_code = 500
            dummy_response._content = b"Request failed after all retries."
            logger.error("Returning a dummy response with status code 500.")
            return dummy_response

    def unlink_bitmoji(self) -> bool:
        """
        Unlink Bitmoji from the Snapchat account.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            url = "https://aws.api.snapchat.com/snapchat.bitmoji.accounts.v1.Accounts/UnlinkAccount"
            headers = {
                'x-snap-access-token': self.device['x-snap-access-token'],
                'content-type': 'application/grpc',
                'user-agent': self.device['grpc-user-agent'],
                'x-request-id': str(uuid.uuid4())
            }

            content = bytes([0, 0, 0, 0, 0])

            response = self.snapchat.client.post(
                url,
                headers=headers,
                content=content
            )

            print(f"""
            body resp: {response.content}
            header resp: {response.headers}
            status resp: {response.status_code}
            """)

            # Check if request was successful (status code 200)
            return response.status_code == 200

        except Exception as e:
            print(f"Unexpected error during Bitmoji unlink: {e}")
            return False
