# utils/config_generator.py (نسخه نهایی و جامع با روش الگوسازی هوشمند)

import json
import logging
import uuid
import datetime
import random
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
        if not profile_details: return None, None
        inbounds_to_create = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        return self._build_configs(user_telegram_id, inbounds_to_create, total_gb, duration_days, custom_remark)

    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        all_generated_configs, generated_uuids = [], []
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        shared_sub_id = generate_random_string(16)

        inbounds_by_server = {}
        for info in inbounds_list:
            server_id = info['server']['id']
            if server_id not in inbounds_by_server: inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(info)

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
                inbound_id = s_inbound['inbound_id']
                inbound_details = api_client.get_inbound(inbound_id)
                if not inbound_details:
                    logger.warning(f"Could not fetch full details for inbound ID {inbound_id}.")
                    continue

                client_uuid = str(uuid.uuid4())
                unique_email = f"in{inbound_id}.{base_client_email}"
                remark_base = custom_remark or f"AlamorBot-{user_telegram_id}"
                
                try:
                    protocol_settings = json.loads(inbound_details.get('settings', '{}'))
                    flow = protocol_settings.get('clients', [{}])[0].get('flow', '')
                except (json.JSONDecodeError, IndexError):
                    flow = ''

                client_settings = {
                    "id": client_uuid, "email": unique_email,
                    "totalGB": total_traffic_bytes, "expiryTime": expiry_time_ms,
                    "enable": True, "tgId": str(user_telegram_id), "subId": shared_sub_id, "flow": flow
                }
                
                add_client_payload = {"id": inbound_id, "settings": json.dumps({"clients": [client_settings]})}
                if not api_client.add_client(add_client_payload):
                    logger.error(f"Failed to add client to inbound {inbound_id} on server {server_id}.")
                    continue

                generated_uuids.append(client_uuid)
                single_config = self._generate_single_config_url(client_uuid, server_data, inbound_details, remark_base)
                if single_config:
                    all_generated_configs.append(single_config)

        client_details_for_db = {'uuids': generated_uuids, 'email': base_client_email, 'sub_id': shared_sub_id}
        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)

    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        لینک کانفیگ را با خواندن هوشمند تمام پارامترها از ساختار JSON پنل تولید می‌کند.
        """
        try:
            protocol = inbound_details.get('protocol')
            if protocol != 'vless': return None

            remark = f"{remark_prefix}-{inbound_details.get('remark', server_data['name'])}"
            address = server_data['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')
            
            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            protocol_settings = json.loads(inbound_details.get('settings', '{}'))
            
            params = {
                'type': stream_settings.get('network', 'tcp'),
                'security': stream_settings.get('security', 'none')
            }
            
            client_in_settings = protocol_settings.get('clients', [{}])[0]
            if client_in_settings.get('flow'):
                params['flow'] = client_in_settings['flow']

            # --- استخراج هوشمند پارامترها از الگو ---
            transport_settings = stream_settings.get(f"{params['type']}Settings", {})
            if 'path' in transport_settings: params['path'] = transport_settings['path']
            if 'host' in transport_settings: params['host'] = transport_settings['host']
            if 'serviceName' in transport_settings: params['serviceName'] = transport_settings['serviceName']
            
            if params['security'] != 'none':
                security_settings = stream_settings.get(f"{params['security']}Settings", {})
                if 'serverName' in security_settings: params['sni'] = security_settings['serverName']
                if 'publicKey' in security_settings: params['pbk'] = security_settings['publicKey']
                if 'shortId' in security_settings: 
                    sid_list = security_settings['shortIds']
                    if sid_list: params['sid'] = random.choice(sid_list)
                if 'spiderX' in security_settings: params['spiderX'] = security_settings['spiderX']

                # استخراج تودرتو
                nested_security_settings = security_settings.get('settings', {})
                if 'fingerprint' in nested_security_settings: params['fp'] = nested_security_settings['fingerprint']
                if 'publicKey' in nested_security_settings: params['pbk'] = nested_security_settings['publicKey']
                if 'spiderX' in nested_security_settings: params['spiderX'] = nested_security_settings['spiderX']

            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v and k != 'security' or (k == 'security' and v != 'none')])
            
            return f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"
        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
            return None