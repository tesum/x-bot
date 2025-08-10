import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import List

load_dotenv()

class Config(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMINS: List[int] = Field(default_factory=list)
    XUI_API_URL: str = os.getenv("XUI_API_URL", "http://localhost:54321")
    XUI_USERNAME: str = os.getenv("XUI_USERNAME", "admin")
    XUI_PASSWORD: str = os.getenv("XUI_PASSWORD", "admin")
    XUI_HOST: str = os.getenv("XUI_HOST", "your-server.com")
    PAYMENT_TOKEN: str = os.getenv("PAYMENT_TOKEN", "")
    
    PRICES: dict = {
        1: 100,
        3: 280,
        6: 500,
        12: 900
    }
    DISCOUNT_PERCENT: int = 10

    @field_validator('ADMINS', mode='before')
    def parse_admins(cls, value):
        if isinstance(value, str):
            return [int(admin) for admin in value.split(",") if admin.strip()]
        return value or []

config = Config(
    ADMINS=os.getenv("ADMINS", "")
)