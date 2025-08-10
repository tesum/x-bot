# functions.py (исправленная версия)
import aiohttp
import logging
from config import config

logger = logging.getLogger(__name__)

async def create_vless_profile(telegram_id: int) -> str:
    """Создание VLESS профиля через 3x-UI API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Аутентификация
            auth_data = {"username": config.XUI_USERNAME, "password": config.XUI_PASSWORD}
            async with session.post(f"{config.XUI_API_URL}/login", json=auth_data) as resp:
                # Проверяем статус ответа
                if resp.status != 200:
                    logger.error(f"Auth failed with status: {resp.status}")
                    return None
                
                # Пытаемся получить JSON или читаем текст
                try:
                    auth_result = await resp.json()
                except aiohttp.ContentTypeError:
                    text = await resp.text()
                    logger.debug(f"Auth response text: {text}")
                    # Попробуем проверить успешность по тексту
                    if "success" in text.lower():
                        logger.info("Auth succeeded by text check")
                    else:
                        logger.error(f"Auth failed: {text}")
                        return None
            
            # Создание профиля
            profile_data = {
                "protocol": "vless",
                "settings": {"clients": [{"id": str(telegram_id), "flow": "xtls-rprx-direct"}]},
                "streamSettings": {"network": "tcp"},
                "tag": f"user_{telegram_id}",
                "port": 443
            }
            
            async with session.post(f"{config.XUI_API_URL}/inbounds", json=profile_data) as resp:
                logger.debug(f"Create profile response: {resp}")
                # Проверяем статус ответа
                if resp.status != 200:
                    logger.error(f"Profile creation failed with status: {resp.status}")
                    return None
                
                # Пытаемся получить JSON или читаем текст
                try:
                    result = await resp.json()
                    if result.get("success"):
                        logger.info(f"Profile created for {telegram_id}")
                        return result["id"]
                    else:
                        logger.error(f"Profile creation failed: {result}")
                except aiohttp.ContentTypeError:
                    text = await resp.text()
                    logger.debug(f"Create profile response text: {text}")
                    # Попробуем найти ID в текстовом ответе
                    if "id" in text.lower():
                        # Пытаемся извлечь ID из текста
                        import re
                        match = re.search(r'"id"\s*:\s*"([^"]+)"', text)
                        if match:
                            profile_id = match.group(1)
                            logger.info(f"Extracted profile ID from text: {profile_id}")
                            return profile_id
                        else:
                            logger.error("Failed to extract ID from text response")
                    else:
                        logger.error("Profile creation failed with text response")
    
    except Exception as e:
        logger.exception(f"API error: {e}")
    return None

async def get_user_stats(profile_id: str) -> dict:
    """Получение статистики профиля"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.XUI_API_URL}/inbounds/{profile_id}/stats") as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except aiohttp.ContentTypeError:
                        text = await resp.text()
                        logger.debug(f"Stats response text: {text}")
                        # Пытаемся разобрать текстовый ответ
                        if "upload" in text and "download" in text:
                            import re
                            upload = re.search(r'"upload"\s*:\s*(\d+)', text)
                            download = re.search(r'"download"\s*:\s*(\d+)', text)
                            if upload and download:
                                return {
                                    "upload": int(upload.group(1)),
                                    "download": int(download.group(1))
                                }
                logger.error(f"Stats request failed with status: {resp.status}")
    except Exception as e:
        logger.error(f"Stats error: {e}")
    return {"upload": 0, "download": 0}

async def generate_vless_url(profile_id: str, telegram_id: int, host: str) -> str:
    """Генерация VLESS ссылки"""
    return f"vless://{profile_id}@{host}:443?security=tls&flow=xtls-rprx-direct#TG{telegram_id}"