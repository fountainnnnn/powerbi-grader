from pydantic import BaseModel


class AppLoginRequest(BaseModel):
    username: str
    password: str


class AppLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
