import base64
import json
import struct
import uuid
from google.protobuf.json_format import ParseDict
from app.protos import SCFriendingFriendActionServiceRequests_pb2
from app.utils.snapkat_utils import SnapkatUtils


class FriendActionEncoder:
    """
    Utility class for encoding friend action requests into a Protobuf formatted payload.
    """

    @staticmethod
    def _uuid_to_proto_uuid(uuid_str: str) -> dict:
        """
        Converts a UUID string into a dictionary with 'highBits' and 'lowBits' suitable for Protobuf.

        Args:
            uuid_str (str): The UUID string to convert.

        Returns:
            dict: A dictionary with keys 'highBits' and 'lowBits'.
        """
        # Convert UUID string to a 128-bit integer
        uuid_int = int(uuid.UUID(uuid_str))

        # Extract the high and low 64-bit parts
        high_bits = (uuid_int >> 64) & 0xFFFFFFFFFFFFFFFF
        low_bits = uuid_int & 0xFFFFFFFFFFFFFFFF

        return {"highBits": high_bits, "lowBits": low_bits}

    @staticmethod
    def _transform_friend_ids(data: dict) -> dict:
        """
        Transforms keys and values in the input dictionary:
        - Changes the top-level key 'users' to 'paramsArray'.
        - Renames 'friend_id' to 'friendId' (transforming its UUID) and
          'suggestion_token' to 'suggestionToken' in each entry.
        - Removes old keys from the final object.
        - Retains all other keys unchanged.

        Args:
            data (dict): The input dictionary containing friend data under the key 'users'.

        Returns:
            dict: The modified dictionary with renamed keys and transformed values.
        """
        # Initialize a new list to hold transformed entries
        transformed_entries = []

        # Iterate over each item in the original 'users' list
        for param in data.get('users', []):
            new_entry = {}
            for key, value in param.items():
                # Rename and transform keys as specified
                if key == 'friend_id' and value:
                    new_entry['friendId'] = FriendActionEncoder._uuid_to_proto_uuid(value)
                elif key == 'suggestion_token':
                    new_entry['suggestionToken'] = value
                else:
                    # Copy any other keys unchanged
                    new_entry[key] = value
            new_entry['source'] = 'ADDED_BY_SUGGESTED'
            transformed_entries.append(new_entry)

        # Remove the old 'users' key
        if 'users' in data:
            del data['users']

        # Set the new top-level key 'paramsArray' with transformed entries
        data['paramsArray'] = transformed_entries

        return data

    @staticmethod
    def encode_request(data_dict: dict) -> bytes:
        """
        Encodes the given dictionary into a Protobuf-serialized payload with a custom header.

        Args:
            data_dict (dict): The input dictionary to encode.

        Returns:
            bytes: The final payload ready to be sent.
        """
        # Transform friendId fields in the input data
        transformed_data = FriendActionEncoder._transform_friend_ids(data_dict)

        # Create a Protobuf message instance for the friend add request
        protobuf_message = SCFriendingFriendActionServiceRequests_pb2.SCFriendingFriendsAddRequest()

        # Populate the Protobuf message with the transformed data
        ParseDict(transformed_data, protobuf_message)

        # Serialize the Protobuf message to bytes
        serialized_data = protobuf_message.SerializeToString()

        as_list = list(serialized_data)

        result = {
            'additional_request_headers': None,
            'request_content_type': 'GRPC',
            'request_payload': as_list,
            'request_url': 'https://aws.api.snapchat.com/snapchat.friending.server.FriendAction/AddFriends',
            'response_content_type': 'GRPC'
        }

        return result
