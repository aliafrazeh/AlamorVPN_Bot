# utils/config_generator.py (نسخه نهایی با معماری دریافت از ساب پنل)

import json
import logging
import uuid
import datetime
import requests
import base64
from urllib.parse import quote

from .helpers import generate_random_string
from api_client.factory import get_api_client
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        logger.info("ConfigGenerator with panel-based subscription logic initialized.")

    def create_subscription_for_profile(self, user_telegram_id: int, profile_id: int, total_gb: float, custom_remark: str = None):
        profile_details = self.db_manager.get_profile_by_id(profile_id)
        if not profile_details: return None, None
        inbounds = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        return self._build_configs(user_telegram_id, inbounds, total_gb, duration_days, custom_remark)

    def create_subscription_for_server(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int, custom_remark: str = None):
        # --- اصلاح اصلی اینجاست ---
        # نام تابع اشتباه به نام صحیح تغییر کرد
        inbounds = self.db_manager.get_active_inbounds_for_server_with_template(server_id)
        
        return self._build_configs(user_telegram_id, inbounds, total_gb, duration_days, custom_remark)

    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        brand_name = self.db_manager.get_setting('brand_name') or "Alamor"

        all_final_configs, all_generated_uuids = [], []
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        shared_sub_id = generate_random_string(16)
        
        inbounds_by_server = {}
        for info in inbounds_list:
            server_id = info['server']['id']
            if server_id not in inbounds_by_server: inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(info)

        expiry_time_ms = 0
        if duration_days and duration_days > 0:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
            expiry_time_ms = int(expire_date.timestamp() * 1000)
            
        total_traffic_bytes = int(total_gb * (1024**3)) if total_gb and total_gb > 0 else 0

        for server_id, inbounds_on_server in inbounds_by_server.items():
            server_data = inbounds_on_server[0]['server']
            api_client = get_api_client(server_data)
            if not api_client or not api_client.check_login():
                logger.error(f"Could not connect to server {server_data['name']}. Skipping.")
                continue

            uuids_on_this_server = []
            for s_inbound in inbounds_on_server:
                inbound_id = s_inbound['inbound_id']
                client_uuid = str(uuid.uuid4())
                
                client_settings = {
                    "id": client_uuid, "email": f"in{inbound_id}.{base_client_email}",
                    "totalGB": total_traffic_bytes, "expiryTime": expiry_time_ms,
                    "enable": True, "tgId": str(user_telegram_id), "subId": shared_sub_id
                }
                
                add_client_payload = {"id": inbound_id, "settings": json.dumps({"clients": [client_settings]})}
                if api_client.add_client(add_client_payload):
                    all_generated_uuids.append(client_uuid)
                    uuids_on_this_server.append(client_uuid)
                else:
                    logger.error(f"Failed to add client to inbound {inbound_id} on server {server_id}.")

            if not uuids_on_this_server:
                logger.error(f"No clients were created on server {server_data['name']}. Skipping subscription fetch.")
                continue

            try:
                panel_sub_url = f"{server_data['subscription_base_url'].rstrip('/')}/{server_data['subscription_path_prefix'].strip('/')}/{shared_sub_id}"
                response = requests.get(panel_sub_url, timeout=20, verify=False)
                response.raise_for_status()
                
                # --- اصلاح اصلی و نهایی اینجاست ---
                decoded_content = ""
                try:
                    # تلاش برای دیکود کردن به عنوان Base64 (برای پنل سنایی)
                    decoded_content = base64.b64decode(response.content).decode('utf-8')
                    logger.info(f"Successfully decoded Base64 subscription from server {server_data['name']}.")
                except Exception:
                    # اگر دیکود Base64 شکست خورد، فرض می‌کنیم متن خام است (برای پنل علیرضا)
                    logger.info(f"Could not decode as Base64. Assuming plain text response from server {server_data['name']}.")
                    decoded_content = response.text

                all_configs_from_panel = decoded_content.strip().split('\n')
                
                user_configs_from_this_server = [
                    config for config in all_configs_from_panel 
                    if any(uuid in config for uuid in uuids_on_this_server)
                ]
                all_final_configs.extend(user_configs_from_this_server)
            except Exception as e:
                logger.error(f"Error fetching/parsing panel subscription for server {server_id}: {e}")

        final_remarked_configs = []
        final_remark_str = custom_remark or f"{brand_name}-{user_telegram_id}"
        for config in all_final_configs:
            base_config = config.split('#', 1)[0]
            final_remarked_configs.append(f"{base_config}#{quote(final_remark_str)}")

        client_details_for_db = {'uuids': all_generated_uuids, 'email': base_client_email}
        return (final_remarked_configs, client_details_for_db) if final_remarked_configs else (None, None)