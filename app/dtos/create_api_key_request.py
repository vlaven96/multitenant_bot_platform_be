from pydantic import BaseModel
class CreateAPIKeyRequest(BaseModel):
    service_name: str