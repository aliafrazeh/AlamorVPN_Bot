# utils/config_generator.py (نسخه نهایی و یکپارچه)

import json
import logging
import uuid
import datetime
from urllib.parse import quote

# ایمپورت‌های پروژه
from .helpers import generate_random_string
from api_client.factory import get_api_client

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self, db_manager):
        """سازنده کلاس که فقط به db_manager نیاز دارد."""
        self.db_manager = db_manager
        logger.info("ConfigGenerator initialized.")

    def create_subscription_for_profile(self, user_telegram_id: int, profile_id: int, total_gb: float, custom_remark: str = None):
        """کانفیگ‌های یک پروفایل را بر اساس اینباندهای تعریف شده برای آن می‌سازد."""
        profile_details = self.db_manager.get_profile_by_id(profile_id)
        if not profile_details:
            return None, None
        
        inbounds_to_create = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        
        return self._build_configs(user_telegram_id, inbounds_to_create, total_gb, duration_days, custom_remark)

    def create_subscription_for_server(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int, custom_remark: str = None):
        """کانفیگ‌ها را برای یک سرور خاص بر اساس اینباندهای فعال آن می‌سازد."""
        inbounds_list_raw = self.db_manager.get_server_inbounds(server_id, only_active=True)
        if not inbounds_list_raw:
            return None, None
        
        server_data = self.db_manager.get_server_by_id(server_id)
        # تبدیل به فرمتی که _build_configs انتظار دارد
        inbounds_to_create = [{'inbound_id': i['inbound_id'], 'server': server_data} for i in inbounds_list_raw]
        
        return self._build_configs(user_telegram_id, inbounds_to_create, total_gb, duration_days, custom_remark)

    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        """
        موتور اصلی ساخت کانفیگ با ایمیل‌های منحصر به فرد و خروجی صحیح.
        """
        all_generated_configs = []
        
        master_client_uuid = str(uuid.uuid4())
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        
        # --- اصلاح مشکل KeyError: 'uuids' ---
        # خروجی باید شامل کلید 'uuids' به صورت لیست باشد
        client_details_for_db = {
            'uuids': [master_client_uuid], # UUID را به صورت لیست برمی‌گردانیم
            'email': base_client_email 
        }

        inbounds_by_server = {}
        for inbound_info in inbounds_list:
            server_id = inbound_info['server']['id']
            if server_id not in inbounds_by_server:
                inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(inbound_info)

        for server_id, inbounds in inbounds_by_server.items():
            server_data = inbounds[0]['server']
            api_client = get_api_client(server_data)
            
            if not api_client or not api_client.check_login():
                logger.error(f"Could not connect to server {server_data['name']} (ID: {server_id}). Skipping.")
                continue

            panel_inbounds_details = {i['id']: i for i in api_client.list_inbounds()}
            if not panel_inbounds_details:
                logger.error(f"Could not retrieve any inbound details from server {server_id}.")
                continue

            expiry_time_ms = 0
            if duration_days and duration_days > 0:
                expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
                expiry_time_ms = int(expire_date.timestamp() * 1000)
            
            total_traffic_bytes = int(total_gb * (1024**3)) if total_gb and total_gb > 0 else 0

            for s_inbound in inbounds:
                inbound_id_on_panel = s_inbound['inbound_id']
                remark = custom_remark or f"AlamorBot-{user_telegram_id}"
                
                # --- اصلاح مشکل Duplicate email ---
                # برای هر اینباند یک ایمیل منحصر به فرد می‌سازیم
                unique_client_email = f"in{inbound_id_on_panel}.{base_client_email}"

                client_settings = {
                    "id": master_client_uuid, 
                    "email": unique_client_email, # استفاده از ایمیل منحصر به فرد
                    "totalGB": total_traffic_bytes, "expiryTime": expiry_time_ms,
                    "enable": True, "tgId": str(user_telegram_id)
                }
                
                add_client_payload = {
                    "id": inbound_id_on_panel,
                    "settings": json.dumps({"clients": [client_settings]})
                }
                
                if not api_client.add_client(add_client_payload):
                    logger.error(f"Failed to add client to inbound {inbound_id_on_panel} on server {server_id}.")
                    continue

                inbound_details = panel_inbounds_details.get(inbound_id_on_panel)
                if inbound_details:
                    single_config = self._generate_single_config_url(
                        master_client_uuid, server_data, inbound_details, remark
                    )
                    if single_config:
                        all_generated_configs.append(single_config)

        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)
    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        این تابع نسخه کامل شده شما برای ساخت لینک‌های پیچیده VLESS است.
        """
        try:
            protocol = inbound_details.get('protocol')
            remark = f"{remark_prefix}-{inbound_details.get('remark', server_data['name'])}"
            # آدرس را از subscription_base_url استخراج می‌کنیم
            address = server_data['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')
            
            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            network = stream_settings.get('network', 'tcp')
            security = stream_settings.get('security', 'none')
            config_url = ""

            if protocol == 'vless':
                # استخراج flow از settings به جای streamSettings
                protocol_settings = json.loads(inbound_details.get('settings', '{}'))
                client_in_settings = protocol_settings.get('clients', [{}])[0]
                flow = client_in_settings.get('flow', '')

                params = {'type': network, 'security': security}
                
                if security == 'reality':
                    reality_settings = stream_settings.get('realitySettings', {})
                    params['fp'] = reality_settings.get('fingerprint', '')
                    params['pbk'] = reality_settings.get('publicKey', '')
                    params['sid'] = reality_settings.get('shortId', '')
                    # SNI ممکن است لیستی از دامنه‌ها باشد
                    sni_list = reality_settings.get('serverNames', [''])
                    params['sni'] = sni_list[0] if sni_list else ''
                
                if security == 'tls':
                    tls_settings = stream_settings.get('tlsSettings', {})
                    params['sni'] = tls_settings.get('serverName', address)

                if network == 'ws':
                    ws_settings = stream_settings.get('wsSettings', {})
                    params['path'] = ws_settings.get('path', '/')
                    params['host'] = ws_settings.get('headers', {}).get('Host', address)

                if flow:
                    params['flow'] = flow

                query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v])
                config_url = f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"
            
            if config_url:
                return config_url
        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
        return None