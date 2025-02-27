from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = "a3f5c8e9d1b2c3d4e5f67890ab12cd34ef56a7b8c9d0e1f2a3b4c5d6e7f8090a"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1600

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
