import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict

MAX_MESSAGE_LENGTH = 4096

load_dotenv()

class Config(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMINS: List[int] = Field(default_factory=list)
    XUI_HOST: str = os.getenv("XUI_HOST", "your-server.com")
    XUI_BASE_PATH: str = os.getenv("XUI_BASE_PATH", "/panel")
    XUI_API_URL: str = os.getenv("XUI_API_URL", "admin")
    XUI_USERNAME: str = os.getenv("XUI_USERNAME", "admin")
    XUI_PASSWORD: str = os.getenv("XUI_PASSWORD", "admin")
    XUI_SERVER_NAME: str = os.getenv("XUI_SERVER_NAME", "domain.com")
    PAYMENT_TOKEN: str = os.getenv("PAYMENT_TOKEN", "")
    INBOUND_ID: int = Field(default=os.getenv("INBOUND_ID", 1))
    REALITY_PUBLIC_KEY: str = os.getenv("REALITY_PUBLIC_KEY", "")
    REALITY_FINGERPRINT: str = os.getenv("REALITY_FINGERPRINT", "chrome")
    REALITY_SNI: str = os.getenv("REALITY_SNI", "example.com")
    REALITY_SHORT_ID: str = os.getenv("REALITY_SHORT_ID", "1234567890")
    REALITY_SPIDER_X: str = os.getenv("REALITY_SPIDER_X", "/")
    PRICES: Dict[int, Dict[str, int]] = Field(default_factory=dict)
    PROMODAY: int = 1

    @field_validator('PRICES', mode='after')
    def load_prices(path):
        # Настройки цен и скидок
        try:
            with open("prices.json", 'r', encoding='utf-8') as f:
                prices = json.load(f)
                print("✅ Тарифы загружены:")
                for key, value in prices.items():
                    print(f"   {key}: {value}")
            # Преобразование ключей в int для удобства
            return {int(k): v for k, v in prices.items()}
        except Exception as e:
            print(f"Ошибка загрузки тарифов: {e}")

    @field_validator('ADMINS', mode='before')
    def parse_admins(cls, value):
        if isinstance(value, str):
            return [int(admin) for admin in value.split(",") if admin.strip()]
        return value or []
    
    @field_validator('INBOUND_ID', mode='before')
    def parse_inbound_id(cls, value):
        if isinstance(value, str):
            return int(value)
        return value or 15

config = Config(
    ADMINS=os.getenv("ADMINS", ""),
    INBOUND_ID=os.getenv("INBOUND_ID", 15),
    PRICES={}
)