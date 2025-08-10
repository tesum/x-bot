# functions.py (исправленная версия)
import aiohttp
import uuid
import json
import logging
import random
import string
import re
from urllib.parse import quote
from config import config

logger = logging.getLogger(__name__)

class XUIAPI:
    def __init__(self):
        self.session = None
        self.cookie_jar = aiohttp.CookieJar()

    async def login(self):
        """Аутентификация в 3x-UI API"""
        try:
            self.session = aiohttp.ClientSession(cookie_jar=self.cookie_jar)
            auth_data = {
                "username": config.XUI_USERNAME,
                "password": config.XUI_PASSWORD
            }
            
            # Формируем URL
            login_url = f"{config.XUI_API_URL}/login"
            
            async with self.session.post(login_url, data=auth_data) as resp:
                # Обрабатываем различные форматы ответов
                content_type = resp.headers.get('Content-Type', '').lower()
                if resp.status != 200:
                    logger.error(f"Login failed with status: {resp.status}")
                    return False
                
                # Обработка текстовых ответов
                if 'text/plain' in content_type or 'text/html' in content_type:
                    text = await resp.text()
                    logger.debug(f"Login response text: {text}")
                    return "success" in text.lower()
                
                # Обработка JSON ответов
                try:
                    response = await resp.json()
                    return resp.headers
                except:
                    return False
        except Exception as e:
            logger.exception(f"Login error: {e}")
            return False

    async def create_vless_profile(self, telegram_id: int):
        """Создание VLESS профиля через 3x-UI API"""
        authData = None
        try:
            authData = await self.login()
            logger.debug(f"Cookie: {authData.get('set-cookie', '')}")
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
        
        try:
            # Генерируем уникальные параметры
            client_id = str(uuid.uuid4())
            email = f"user_{telegram_id}_{random.randint(1000,9999)}"
            port = random.randint(20000, 50000)
            
            # Параметры клиента
            client_settings = {
                "id": client_id,
                "flow": "xtls-rprx-vision",
                "email": email,
                "limitIp": 0,
                "totalGB": 0,
                "expiryTime": 0,
                "enable": True,
                "tgId": "",
                "subId": "",
                "reset": 0
            }
            
            # Настройки инбаунда
            settings = {
                "clients": [client_settings],
                "decryption": "none",
                "fallbacks": []
            }
            
            # Настройки потока
            stream_settings = {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "teamdocs.su:443",
                    "serverNames": ["teamdocs.su"],
                    "show": False,
                    "xver": 0,
                    "serverName": "teamdocs.su",
                    "privateKey": generate_random_key(),
                    "settings": {
                        "publicKey": generate_random_key(),
                        "fingerprint": "chrome"
                    },
                },
                "tcpSettings": {
                    "header": {
                        "type": "none"
                    },
                    "acceptProxyProtocol": False
                }
            }
            
            # Данные для создания инбаунда
            data = {
                "up": 0,
                "down": 0,
                "total": 0,
                "remark": f"Telegram User {telegram_id}",
                "enable": True,
                "expiryTime": 0,
                "listen": "",
                "port": port,
                "protocol": "vless",
                "settings": json.dumps(settings),
                "streamSettings": json.dumps(stream_settings),
                "sniffing": json.dumps({
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic", "fakedns"],
                    "metadataOnly": False,
                    "routeOnly": False
                }),
                "allocate": json.dumps({
                    "strategy": "always",
                    "refresh": 5,
                    "concurrency": 3
                })
            }
            
            # Формируем URL для создания инбаунда
            create_url = f"{config.XUI_API_URL}/panel/api/inbounds/add"
            cookie_set = authData.get('set-cookie', '')
            
            # Отправляем запрос на создание
            async with self.session.post(create_url, data=data, headers={"Cookie": cookie_set}) as resp:
                content_type = resp.headers.get('Content-Type', '').lower()
                response_text = await resp.text()
                logger.debug(f"Create profile response: {response_text[:500]}...")
                
                # Обработка текстовых ответов
                if 'text/plain' in content_type or 'text/html' in content_type:
                    # Пытаемся извлечь ID из текстового ответа
                    match = re.search(r'"id"\s*:\s*(\d+)', response_text)
                    if match:
                        return {
                            "inbound_id": int(match.group(1)),
                            "client_id": client_id,
                            "email": email,
                            "port": port,
                            "security": "tls"
                        }
                    return None
                
                # Обработка JSON ответов
                try:
                    response = await resp.json()
                    if response.get("success", False):
                        return {
                            "inbound_id": response["obj"]["id"],
                            "client_id": client_id,
                            "email": email,
                            "port": port,
                            "security": "tls"
                        }
                except:
                    return None
        except Exception as e:
            logger.exception(f"Create profile error: {e}")
        return None

    async def get_user_stats(self, email: str):
        """Получение статистики профиля по email"""
        if not await self.login():
            logger.error("Failed to authenticate before getting stats")
            return {"upload": 0, "download": 0}
        
        try:
            # Формируем URL для получения статистики
            base_url = config.XUI_API_URL.rstrip('/')
            stats_url = f"{base_url}/panel/api/inbounds/getClientTraffics/{email}"
            
            async with self.session.get(stats_url) as resp:
                content_type = resp.headers.get('Content-Type', '').lower()
                response_text = await resp.text()
                
                # Обработка текстовых ответов
                if 'text/plain' in content_type or 'text/html' in content_type:
                    # Пытаемся извлечь статистику из текста
                    upload_match = re.search(r'"up"\s*:\s*(\d+)', response_text)
                    download_match = re.search(r'"down"\s*:\s*(\d+)', response_text)
                    
                    return {
                        "upload": int(upload_match.group(1)) if upload_match else 0,
                        "download": int(download_match.group(1)) if download_match else 0
                    }
                
                # Обработка JSON ответов
                try:
                    response = await resp.json()
                    if response.get("success", False) and response.get("obj"):
                        return {
                            "upload": response["obj"].get("up", 0),
                            "download": response["obj"].get("down", 0)
                        }
                except:
                    return {"upload": 0, "download": 0}
        except Exception as e:
            logger.error(f"Stats error: {e}")
        return {"upload": 0, "download": 0}

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()

async def create_vless_profile(telegram_id: int):
    """Создание VLESS профиля"""
    api = XUIAPI()
    try:
        return await api.create_vless_profile(telegram_id)
    finally:
        await api.close()

async def get_user_stats(email: str):
    """Получение статистики по email"""
    api = XUIAPI()
    try:
        return await api.get_user_stats(email)
    finally:
        await api.close()

def generate_random_key(length=44) -> str:
    """
    Генерация случайного ключа, похожего на пример,
    с символами A-Z, a-z, 0-9, '-' и '_'
    """
    allowed_chars = string.ascii_letters + string.digits + "-_"
    return ''.join(random.choice(allowed_chars) for _ in range(length))

def generate_vless_url(profile_data: dict) -> str:
    """Генерация VLESS ссылки с дополнительными параметрами"""
    # Чтобы безопасно вставить alpn и другие параметры с символами
    alpn = quote("http/1.1")  # кодируем для URL
    
    user_tag = profile_data['email'].split('_')[1] if 'email' in profile_data and '_' in profile_data['email'] else "user"
    
    return (
        f"vless://{profile_data['client_id']}@{config.XUI_HOST}:{profile_data['port']}"
        f"?type=tcp&security={profile_data['security']}&fp=chrome&alpn={alpn}"
        f"&sni={config.XUI_SERVER_NAME}&flow=xtls-rprx-direct"
        f"#Telegram%20User%20{user_tag}-{profile_data['email']}"
    )