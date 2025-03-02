from redis.asyncio import Redis
import asyncio
import requests
from datetime import datetime
import base64
import json
from app.database import AsyncSessionLocal
from app.schemas.snapkat_request_log import SnapkatRequestLog
from app.utils.event_loop_manager import get_or_create_event_loop
import time

class HttpRequestHandler:
    def __init__(self, redis_url="redis://localhost:6379/1"):
        self.redis = Redis.from_url(redis_url)


    def make_request(self, method: str, url: str, headers: dict = None,
                           json: dict = None, data: bytes = None, params: dict = None, proxies: dict = None, **kwargs):
        """
        Generic HTTP request handler with support for various request options.

        :param method: HTTP method (e.g., "GET", "POST").
        :param url: URL of the request.
        :param headers: HTTP headers.
        :param json: JSON payload for the request.
        :param data: Raw data for the request.
        :param params: Query parameters for GET requests.
        :param proxies: Proxy configuration.
        :param kwargs: Additional arguments to pass to requests.request.
        :return: Response object.
        """
        max_retries = 3
        response = None
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    # Perform the HTTP request
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json,
                        data=data,
                        params=params,
                        proxies=proxies,
                        **kwargs
                    )
                    break
                except requests.exceptions.ProxyError as e:
                    print(f"Proxy authentication error on attempt {attempt}/{max_retries}: {str(e)}")
                    if attempt < max_retries:
                        print("Retrying in 60 seconds...")
                        time.sleep(60)
                    else:
                        raise RuntimeError(f"Maximum retry attempts reached for proxy error: {str(e)}") from e
                except requests.exceptions.RequestException as e:
                    print(f"Request error on attempt {attempt}/{max_retries}: {str(e)}")
                    if attempt < max_retries:
                        print("Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        raise RuntimeError(f"Maximum retry attempts reached for request error: {str(e)}") from e
            # Check for quota limit exceeded
            if response.status_code == 429 or "quota limit exceeded" in response.text.lower():
                print(f"API quota limit exceeded for URL: {url}. Response not logged.")
                return response  # Return the response but don't log it

            loop = get_or_create_event_loop()

            # Schedule the async method call on that loop
            if response:
                loop.call_soon_threadsafe(
                    asyncio.create_task,
                    self.enqueue_log(
                        url=url,
                        method=method,
                        headers=headers,
                        payload=json if json else data,
                        params=params,
                        response_status=response.status_code,
                        response_body=response.text,
                    )
                )
            return response  # Return the response to the calling method
        except Exception as e:
            print(f"Failed to make request to {url}: {str(e)}")
            raise

    async def enqueue_log(self, url, method, headers, payload, params, response_status, response_body):
        if isinstance(payload, bytes):
            payload = base64.b64encode(payload).decode('utf-8')

            # Handle JSON-compatible payloads (dict or list)
        elif isinstance(payload, (dict, list)):
            payload = json.dumps(payload)

            # If payload is None, use an empty string
        payload = payload if payload is not None else ""

        log_data = {
            'url': url,
            'method': method,
            'headers': json.dumps(headers) if headers else None,
            'payload': payload,
            'params': json.dumps(params) if params else None,
            'response_status': response_status,
            'response_body': response_body,
            'created_at': datetime.utcnow().isoformat(),
        }
        await self.redis.rpush("log_queue", json.dumps(log_data))
        print("DEBUG: Successfully rpush'ed to Redis")

    async def log_worker(self):
        while True:
            _, log_data = await self.redis.blpop("log_queue")
            print(f"DEBUG: Popped data from Redis: {log_data}")
            log_data = json.loads(log_data)  # Deserialize JSON data

            try:
                async with AsyncSessionLocal() as session:
                    request_log = SnapkatRequestLog(
                        url=log_data['url'],
                        method=log_data['method'],
                        headers=log_data['headers'],  # Already serialized as JSON string
                        payload=log_data['payload'],  # Already serialized as JSON string
                        response_status=log_data['response_status'],
                        response_body=log_data['response_body'],
                    )
                    session.add(request_log)
                    await session.commit()
            except Exception as e:
                print(f"Failed to log request: {e}")


