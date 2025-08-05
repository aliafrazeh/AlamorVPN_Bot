# utils/config_generator.py (نسخه نهایی با فراخوانی get_inbound برای هر کانفیگ)

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
        self.db_manager = db_manager
        logger.info("ConfigGenerator initialized.")

    def create_subscription_for_profile(self, user_telegram_id: int, profile_id: int, total_gb: float, custom_remark: str = None):
        profile_details = self.db_manager.get_profile_by_id(profile_id)
        if not profile_details:
            return None, None
        
        inbounds_to_create = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        
        return self._build_configs(user_telegram_id, inbounds_to_create, total_gb, duration_days, custom_remark)

    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        all_generated_configs = []
        generated_uuids = []
        
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        shared_sub_id = generate_random_string(16)

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
                logger.error(f"Could not connect to server {server_data['name']}. Skipping.")
                continue

            expiry_time_ms = 0
            if duration_days and duration_days > 0:
                expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
                expiry_time_ms = int(expire_date.timestamp() * 1000)
            
            total_traffic_bytes = int(total_gb * (1024**3)) if total_gb and total_gb > 0 else 0

            for s_inbound in inbounds:
                inbound_id_on_panel = s_inbound['inbound_id']
                remark_base = custom_remark or f"AlamorBot-{user_telegram_id}"
                
                client_uuid = str(uuid.uuid4())
                unique_client_email = f"in{inbound_id_on_panel}.{base_client_email}"

                client_settings = {
                    "id": client_uuid, "email": unique_client_email,
                    "totalGB": total_traffic_bytes, "expiryTime": expiry_time_ms,
                    "enable": True, "tgId": str(user_telegram_id), "subId": shared_sub_id
                }
                
                add_client_payload = {"id": inbound_id_on_panel, "settings": json.dumps({"clients": [client_settings]})}
                
                if not api_client.add_client(add_client_payload):
                    logger.error(f"Failed to add client to inbound {inbound_id_on_panel} on server {server_id}.")
                    continue

                generated_uuids.append(client_uuid)

                # --- اصلاح اصلی و نهایی اینجاست ---
                # ما برای هر اینباند، جزئیات کامل آن را به صورت جداگانه دریافت می‌کنیم
                inbound_details = api_client.get_inbound(inbound_id_on_panel)
                if inbound_details:
                    single_config = self._generate_single_config_url(
                        client_uuid, server_data, inbound_details, remark_base
                    )
                    if single_config:
                        all_generated_configs.append(single_config)
                else:
                    logger.warning(f"Could not fetch full details for inbound ID {inbound_id_on_panel}.")


        client_details_for_db = { 'uuids': generated_uuids, 'email': base_client_email, 'sub_id': shared_sub_id }
        
        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)
    
    # utils/config_generator.py

    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        لینک کانفیگ را با خواندن صحیح ساختار تودرتوی JSON برای تمام انواع VLESS تولید می‌کند.
        (نسخه نهایی بر اساس خروجی واقعی پنل)
        """
        try:
            protocol = inbound_details.get('protocol')
            if protocol != 'vless':
                logger.warning(f"Config generation for protocol '{protocol}' is not supported yet.")
                return None

            remark = f"{remark_prefix}-{inbound_details.get('remark', server_data['name'])}"
            address = server_data['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')
            
            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            protocol_settings = json.loads(inbound_details.get('settings', '{}'))
            
            # پارامترهای پایه را استخراج می‌کنیم
            params = {
                'type': stream_settings.get('network', 'tcp'),
                'security': stream_settings.get('security', 'none')
            }

            # استخراج 'flow' از تنظیمات اصلی پروتکل
            client_in_settings = protocol_settings.get('clients', [{}])[0]
            flow = client_in_settings.get('flow', '')
            if flow:
                params['flow'] = flow

            # مدیریت تنظیمات TLS
            if params['security'] == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                nested_tls_settings = tls_settings.get('settings', {})
                params['fp'] = nested_tls_settings.get('fingerprint', '')
                params['sni'] = tls_settings.get('serverName', address)

            # مدیریت کامل تنظیمات Reality
            if params['security'] == 'reality':
                reality_settings = stream_settings.get('realitySettings', {})
                nested_reality_settings = reality_settings.get('settings', {})
                
                params['pbk'] = nested_reality_settings.get('publicKey', '')
                params['fp'] = nested_reality_settings.get('fingerprint', '')
                params['spiderX'] = nested_reality_settings.get('spiderX', '')
                
                sni_list = reality_settings.get('serverNames', [''])
                params['sni'] = sni_list[0] if sni_list else ''
                
                short_ids_list = reality_settings.get('shortIds', [''])
                params['sid'] = short_ids_list[0] if short_ids_list else ''

            # مدیریت تنظیمات نوع شبکه (Transport)
            if params['type'] == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                params['path'] = ws_settings.get('path', '')
                params['host'] = ws_settings.get('host', '')
            
            elif params['type'] == 'grpc':
                grpc_settings = stream_settings.get('grpcSettings', {})
                params['serviceName'] = grpc_settings.get('serviceName', '')
                
            elif params['type'] == 'httpupgrade':
                upg_settings = stream_settings.get('httpupgradeSettings', {})
                params['path'] = upg_settings.get('path', '')
                params['host'] = upg_settings.get('host', '')


            # ساخت رشته نهایی و حذف پارامترهای خالی
            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v])
            
            config_url = f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"
            
            return config_url

        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
            return None