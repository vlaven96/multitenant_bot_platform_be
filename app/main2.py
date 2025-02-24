import httpx
import struct
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# URL for Snapchat's gRPC service
url = "https://aws.api.snapchat.com/snapchat.fidelius.FideliusRecryptService/PollRecrypt"

# Headers required for gRPC over HTTP/2
headers = {
    "accept-encoding": "identity,gzip",
    "content-type": "application/grpc",
    "grpc-accept-encoding": "identity,deflate,gzip",
    "grpc-timeout": "30S",  # Reduced from 270S for testing
    "te": "trailers",  # Required for gRPC over HTTP/2
    "user-agent": "Snapchat/12.94.0.39 (iPhone8,1; iOS 15.8.1; gzip) grpc-c++/1.48.0 grpc-c/26.0.0 (ios; cronet_http)",
    "x-request-id": "253c1241-f93e-4163-8827-a77bd175da39",
    "x-snap-access-token": 'hCgwKCjE3MzgwMDA4MjISgAGVru97YVT6DWruLoJKyKro4SWTu9MJoyaBAncZqCWvCcQ_nAzdespiFtjZAxfWDjOyf6BE7p-FJf_0zBBHV_Y3Yt4i0gCWPq1Q4o2P4Av1egMlulsWQpSCQQ0o03T59JOVW6D04hts_OArmSpuLovU6we6ogQpMYdZmSqH_oqQfQ'  # Replace with actual token
}

# Simulated Protobuf-encoded message (this must be correct!)
protobuf_message = b"\nA\x04R\xb1\xe9D\xe0\xc7\x1e\xe9\xbe\x90\xdf\x9aL\xe9[\xea\x18\xb4Rh\x86\x88\x03\xfbp\xfeX\\\xa1\x18^\x1e'y\xa2\x8aF!\x8d\x06A\x0e%\x9e7\xc0\x9ex\xbf\xd8\xec\x00\xe9\xd7X\x1a\xec\xca\xbf\xab\ts\x9d"
# Your original binary content (unchanged)
content = b"\x00\x00\x00\x00C\nA\x04R\xb1\xe9D\xe0\xc7\x1e\xe9\xbe\x90\xdf\x9aL\xe9[\xea\x18\xb4Rh\x86\x88\x03\xfbp\xfeX\\\xa1\x18^\x1e'y\xa2\x8aF!\x8d\x06A\x0e%\x9e7\xc0\x9ex\xbf\xd8\xec\x00\xe9\xd7X\x1a\xec\xca\xbf\xab\ts\x9d"

# Use an HTTP/2-enabled client
transport = httpx.HTTPTransport(http2=True)

# Run request inside `with` statement
with httpx.Client(transport=transport, http2=True) as client:
    response = client.post(url, headers=headers, content=content)

    # Print debugging info
    print("\n==== Response ====")
    print("Status Code:", response.status_code)
    print("Headers:", response.headers)
    print("Content:", response.content)

    # Log HTTP/2 usage
    print("\n==== Debug Info ====")
    print(f"Used HTTP Version: {response.http_version}")
    print(f"Request Length: {len(content)} bytes")
