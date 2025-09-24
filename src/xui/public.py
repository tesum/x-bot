async def create_vless_profile(telegram_id: int):
    api = XUIAPI()
    try:
        return await api.create_vless_profile(telegram_id)
    finally:
        await api.close()

async def create_static_client(profile_name: str):
    api = XUIAPI()
    try:
        return await api.create_static_client(profile_name)
    finally:
        await api.close()

async def delete_client_by_email(email: str):
    api = XUIAPI()
    try:
        return await api.delete_client(email)
    finally:
        await api.close()

async def get_global_stats():
    api = XUIAPI()
    try:
        return await api.get_global_stats(config.INBOUND_ID)
    finally:
        await api.close()

async def get_online_users():
    api = XUIAPI()
    try:
        return await api.get_online_users()
    finally:
        await api.close()

async def get_user_stats(email: str):
    api = XUIAPI()
    try:
        return await api.get_user_stats(email)
    finally:
        await api.close()

def generate_vless_url(profile_data: dict) -> str:
    remark = profile_data.get('remark', '')
    email = profile_data['email']
    fragment = f"{remark}-{email}" if remark else email
    
    return (
        f"vless://{profile_data['client_id']}@{config.XUI_HOST}:{profile_data['port']}"
        f"?type=tcp&security=reality"
        f"&pbk={config.REALITY_PUBLIC_KEY}"
        f"&fp={config.REALITY_FINGERPRINT}"
        f"&sni={config.REALITY_SNI}"
        f"&sid={config.REALITY_SHORT_ID}"
        f"&spx={config.REALITY_SPIDER_X}"
        f"#{fragment}"
    )