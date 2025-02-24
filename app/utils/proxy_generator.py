import random
class ProxyGenerator:
    @staticmethod
    def generate_id():
        characters = '0123456789'
        # Build an 8-character string by randomly selecting digits
        return ''.join(random.choice(characters) for _ in range(8))

    @staticmethod
    def generate_proxy():
        host = "datacenter.proxyempire.io"
        port = "9000"
        session_id = ProxyGenerator.generate_id()
        username = f"3954360552;any;session_{session_id}"
        password = "b4adccb73d"
        return f"http://{username}:{password}@{host}:{port}"