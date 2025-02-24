import uuid
# from datetime import time
import time
import httpx

from app.utils.snapkat_utils import SnapkatUtils


class SnapchatClient():
    def __init__(self, proxies, retries=3, backoff_factor=15):
        self.proxies = proxies
        self.client = httpx.Client(proxies=proxies, http2=True)
        self.retries = retries
        self.backoff_factor = backoff_factor

    def test_proxy(self):
        response = self.client.get("https://httpbin.org/ip")
        print('[proxy-test] resp:', response.text)

    def get_snapchat_headers(self, device, extra={}, with_timestamp=False):
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "user-agent": device["user-agent"],
            "x-snapchat-uuid": str(uuid.uuid4()),
        }
        if with_timestamp:
            pass
        headers.update(extra)
        return headers

    def get_form_headers(self, device, extra={}, with_auth=False):
        req_id = str(uuid.uuid4()).upper()
        request_headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=utf-8',
            'user-agent': device['user-agent'],
            'accept': 'application/json',
            'x-snapchat-uuid': req_id,
            'x-request-id': req_id,
            'accept-language': device['device_language'],
        }

        if with_auth:
            request_headers['x-snap-access-token'] = device['x-snap-access-token']

        if extra:
            request_headers.update(extra)

        return request_headers

    def get_snapchat_grpc_headers(self, device, extra={}, with_timestamp=False, with_auth=False):
        headers = {
            'user-agent': device["grpc-user-agent"],
            'content-type': 'application/grpc',
            'te': 'trailers',
            'grpc-accept-encoding': 'identity,deflate,gzip',
            'accept-encoding': 'identity,gzip',
            'x-request-id': str(uuid.uuid4()),
            'grpc-timeout': '270S',
        }

        if with_timestamp:
            headers['x-snap-janus-request-created-at'] = str(int(time.time() * 1000))

        if with_auth:
            headers["x-snap-access-token"] = device['x-snap-access-token']

        if extra:
            headers.update(extra)

        return headers

    def get_proto_headers(self, device, extra={}, with_auth=False):
        req_id = str(uuid.uuid4()).upper()
        headers = {
            "Accept-Language": device['device_language'],
            "User-Agent": device['user-agent'],
            'x-snapchat-uuid': req_id,
            'x-request-id': req_id,
            'Content-Type': 'application/x-protobuf',
        }
        if with_auth:
            headers['X-Snap-Access-Token'] = device['x-snap-access-token']

        headers.update(extra)
        return headers

    def get_snapchat_binary_headers(self, device, extra={}, with_auth=True):
        req_id = str(uuid.uuid4()).upper()
        headers = {
            'user-agent': device["user-agent"],
            'content-type': 'binary/octet-stream',
            'x-request-id': req_id,
            'x-snapchat-uuid': req_id,
            'x-snap-access-token': device['x-snap-access-token'],
        }

        if extra:
            headers.update(extra)

        if not with_auth:
            del headers['x-snap-access-token']

        return headers

    def make_snapchat_request(
            self,
            url,
            device,
            content,
            extra_headers,
            signed_request_info,
            with_timestamp,
            with_auth
    ):
        headers = self.compute_final_request_headers(device, signed_request_info, with_timestamp, with_auth)
        if extra_headers:
            headers.update(extra_headers)
        # req = self.client.post(url, content=content, headers=headers)
        req = self.request_with_retry("POST", url, content=content, headers=headers)
        response_content_type = signed_request_info['response_content_type']
        if response_content_type == "GRPC":
            return {'respBody': SnapkatUtils.read_request_frame(req.content), 'status': req.status_code}
        else:
            return {'respBody': req.content, 'status': req.status_code}

    def compute_final_request_headers(self, device, signed_request_info, with_timestamp=False, with_auth=False):
        request_content_type = signed_request_info['request_content_type']
        additional_request_headers = signed_request_info['additional_request_headers']
        if request_content_type == "GRPC":
            return self.get_snapchat_grpc_headers(device, additional_request_headers, with_timestamp, with_auth)
        elif request_content_type in ["JSON", "FORM"]:
            return self.get_form_headers(device, additional_request_headers, with_auth)
        elif request_content_type == "PROTO":
            return self.get_proto_headers(device, additional_request_headers, with_auth)
        elif request_content_type == "BINARY":
            return self.get_snapchat_binary_headers(device, additional_request_headers, with_auth)

    def compute_final_request_payload(self, signed_request_info):
        request_payload = bytes(signed_request_info['request_payload'])
        request_content_type = signed_request_info['request_content_type']
        if request_content_type == "GRPC":
            content = SnapkatUtils.write_request_frame(request_payload)
            return content
        elif request_content_type in ["JSON", "FORM"]:
            return request_payload.decode()
        elif request_content_type in ["PROTO", "BINARY"]:
            return request_payload

    def make_binary_request(self, url, device, body, extra, with_auth=True):
        headers = self.get_snapchat_binary_headers(device, extra, with_auth)
        req = self.client.post(url, content=body, headers=headers)
        respBody = req.content
        return {'respBody': respBody, 'status': req.status_code}

    def upload_media(self, upload_url, device, body, extra):
        headers = {
            'Accept': 'application/json',
            'Accept-Language': device['device_language'],
            'X-Snapchat-UUID': str(uuid.uuid4()),
            'User-Agent': device['user-agent'],
            'Content-Type': 'application/octet-stream',
        }
        headers.update(extra)

        req = self.client.put(upload_url, content=body, headers=headers)

        return req.status_code == 200

    def request_with_retry(self, method, url, **kwargs):
        """
        Makes an HTTP request with retry logic.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            url (str): The URL to make the request to.
            **kwargs: Additional arguments for the `httpx.Client.request` method.

        Returns:
            httpx.Response: The response from the server.
        """
        last_response = None
        for attempt in range(self.retries):
            try:
                response = self.client.request(method, url, **kwargs)
                last_response = response
                # Check for HTTP status codes indicating proxy-related issues
                if response.status_code in {407}:  # Proxy authentication required
                    if attempt < self.retries - 1:
                        raise httpx.ProxyError(f"Proxy error: {response.status_code}")
                return response
            except (httpx.ProxyError, httpx.ConnectError, httpx.HTTPStatusError) as e:
                # Log the error and retry
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.retries - 1:
                    time.sleep(self.backoff_factor * (2 ** attempt))  # Exponential backoff
                else:
                    raise
        return last_response