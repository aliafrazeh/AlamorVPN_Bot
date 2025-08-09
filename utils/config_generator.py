# utils/config_generator.py (نسخه نهایی و پایدار)

import json
import logging
import uuid
import datetime
from urllib.parse import urlunparse, quote

# ایمپورت‌های پروژه
from .helpers import generate_random_string
from api_client.factory import get_api_client
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        logger.info("ConfigGenerator with FINAL rebuild logic initialized.")

    def _rebuild_link_from_params(self, params: dict) -> str:
        """
        یک لینک کانفیگ VLESS را از دیکشنری پارامترهای تجزیه شده با دقت کامل بازسازی می‌کند.
        """
        try:
            # ۱. استخراج اجزای اصلی و ساختاری لینک
            scheme = params.get('protocol', 'vless')
            uuid = params.get('uuid')
            hostname = params.get('hostname')
            port = params.get('port')
            remark = params.get('remark', '')
            path = params.get('path', '')

            # ۲. ساخت رشته کوئری (Query String) از تمام پارامترهای باقی‌مانده
            structural_keys = {'protocol', 'uuid', 'hostname', 'port', 'remark', 'path'}
            query_params = {key: value for key, value in params.items() if key not in structural_keys}
            
            sorted_query_params = dict(sorted(query_params.items()))
            
            query_string = '&'.join([f"{key}={quote(str(value))}" for key, value in sorted_query_params.items() if value or value == 0 or value == ''])

            # ۳. بازسازی کامل لینک
            netloc = f"{uuid}@{hostname}:{port}"
            url_parts = (
                scheme,
                netloc,
                path,
                '',  # پارامترهای مسیر که در VLESS استفاده نمی‌شود
                query_string,
                quote(remark)
            )
            
            return urlunparse(url_parts)
        except Exception as e:
            logger.error(f"Error rebuilding link from params: {e}", exc_info=True)
            return None

    def create_subscription_for_profile(self, user_telegram_id: int, profile_id: int, total_gb: float, custom_remark: str = None):
        profile_details = self.db_manager.get_profile_by_id(profile_id)
        if not profile_details: return None, None
        
        inbounds_with_templates = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        
        return self._build_configs_from_template(user_telegram_id, inbounds_with_templates, total_gb, duration_days, custom_remark)

    def create_subscription_for_server(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int, custom_remark: str = None):
        inbounds_with_templates = self.db_manager.get_active_inbounds_for_server_with_template(server_id)
        
        return self._build_configs_from_template(user_telegram_id, inbounds_with_templates, total_gb, duration_days, custom_remark)

    def _build_configs_from_template(self, user_telegram_id: int, inbounds_list_with_templates: list, total_gb: float, duration_days: int, custom_remark: str = None):
        all_generated_configs, generated_uuids = [], []
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        
        inbounds_by_server = {}
        for info in inbounds_list_with_templates:
            server_id = info['server']['id']
            if server_id not in inbounds_by_server: inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(info)

        expiry_time_ms = 0
        if duration_days and duration_days > 0:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
            expiry_time_ms = int(expire_date.timestamp() * 1000)
        total_traffic_bytes = int(total_gb * (1024**3)) if total_gb and total_gb > 0 else 0

        for server_id, inbounds in inbounds_by_server.items():
            server_data = inbounds[0]['server']
            api_client = get_api_client(server_data)
            if not api_client or not api_client.check_login():
                logger.error(f"Could not connect to server {server_data['name']}. Skipping.")
                continue

            for s_inbound in inbounds:
                inbound_id = s_inbound['inbound_id']
                config_params = s_inbound.get('config_params')
                
                if not config_params:
                    logger.warning(f"No config template found for inbound {inbound_id} on server {server_id}. Skipping.")
                    continue

                client_uuid = str(uuid.uuid4())
                unique_email = f"in{inbound_id}.{base_client_email}"
                
                client_settings = {
                    "id": client_uuid, "email": unique_email, "totalGB": total_traffic_bytes,
                    "expiryTime": expiry_time_ms, "enable": True, "tgId": str(user_telegram_id)
                }
                
                add_client_payload = {"id": inbound_id, "settings": json.dumps({"clients": [client_settings]})}
                if not api_client.add_client(add_client_payload):
                    logger.error(f"Failed to add client to inbound {inbound_id} on server {server_id}.")
                    continue

                generated_uuids.append(client_uuid)
                
                # --- بازسازی لینک نهایی از روی الگو ---
                final_params = dict(config_params)
                final_params['uuid'] = client_uuid
                final_params['remark'] = custom_remark or f"AlamorBot-{user_telegram_id}-{s_inbound.get('remark', '')}"
                
                final_config_url = self._rebuild_link_from_params(final_params)
                if final_config_url:
                    all_generated_configs.append(final_config_url)

        client_details_for_db = {'uuids': generated_uuids, 'email': base_client_email}
        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)