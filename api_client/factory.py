# api_client/factory.py

from api_client.xui_api_client import XuiAPIClient
from api_client.alireza_api_client import AlirezaAPIClient
# زمانی که پنل‌های دیگر را اضافه کردیم، آنها را نیز اینجا وارد می‌کنیم
# from api_client.hiddify_api_client import HiddifyAPIClient

import logging

logger = logging.getLogger(__name__)

def get_api_client(server_info: dict):
    """
    این تابع اطلاعات یک سرور را گرفته و بر اساس نوع پنل آن،
    کلاینت API مناسب را برمی‌گرداند.
    """
    panel_type = server_info.get('panel_type', 'x-ui').lower()
    panel_url = server_info.get('panel_url')
    username = server_info.get('username')
    password = server_info.get('password')

    if not all([panel_url, username, password]):
        logger.error("Server information is incomplete. Cannot create API client.")
        return None

    if panel_type == 'alireza':
        logger.info(f"Creating AlirezaAPIClient for server: {server_info.get('name')}")
        return AlirezaAPIClient(panel_url=panel_url, username=username, password=password)
    
    # elif panel_type == 'hiddify':
    #     # در هیدیفای، 'username' همان UUID ادمین است
    #     return HiddifyAPIClient(panel_url=panel_url, admin_uuid=username)

    elif panel_type == 'x-ui':
        logger.info(f"Creating default XuiAPIClient for server: {server_info.get('name')}")
        return XuiAPIClient(panel_url=panel_url, username=username, password=password)
    
    else:
        logger.error(f"Unknown panel type: '{panel_type}'. Cannot create API client.")
        return None