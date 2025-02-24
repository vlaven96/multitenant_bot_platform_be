import base64
import json
from google.protobuf.json_format import MessageToDict
from app.protos import argos_pb2

class ArgosTokenDecoder:
    """
    Utility class for decoding and processing Snapchat Argos token Protobuf responses.
    """

    @staticmethod
    def _decode_base64_token(base64_string: str) -> bytes:
        """
        Decodes a Base64-encoded token into raw bytes.
        """
        return base64.b64decode(base64_string)

    @staticmethod
    def _process_decoded_argos_response(decoded_dict: dict) -> dict:
        """
        Processes the decoded Argos Protobuf JSON structure:
        - Converts Base64-encoded tokens to raw bytes.
        - Ensures the response structure is correctly formatted.
        """
        try:
            decoded_dict['response']['token1']['argos_token']['token'] = ArgosTokenDecoder._decode_base64_token(
                decoded_dict['response']['token1']['argos_token']['token']
            )
            decoded_dict['response']['token2']['argos_token']['token'] = ArgosTokenDecoder._decode_base64_token(
                decoded_dict['response']['token2']['argos_token']['token']
            )
        except KeyError as e:
            raise ValueError(f"Missing key in decoded Argos response: {e}")

        return decoded_dict['response']

    @staticmethod
    def decode_argos_protobuf_response(raw_bytes: bytes) -> dict:
        """
        Decodes a Base64-encoded Snapchat Argos Protobuf response.
        - Extracts raw Protobuf bytes.
        - Parses the Protobuf message into a structured object.
        - Converts it to JSON with corrected token formats.
        """
        try:
            # Decode Base64 string to raw binary
            # raw_bytes = base64.b64decode(base64_encoded_response)

            # Parse Argos Protobuf message
            decoded_message = argos_pb2.ArgosGetTokensResponse()
            decoded_message.ParseFromString(raw_bytes)

            # Convert Protobuf message to a dictionary
            decoded_dict = MessageToDict(decoded_message, preserving_proto_field_name=True)

            # Process the JSON structure for correct formatting
            formatted_json = ArgosTokenDecoder._process_decoded_argos_response(decoded_dict)

            return formatted_json

        except Exception as e:
            raise ValueError(f"Failed to decode Argos Protobuf response: {e}")
