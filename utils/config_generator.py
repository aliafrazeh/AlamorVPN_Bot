# utils/config_generator.py (نسخه نهایی و هوشمند)

import json
import logging
import uuid
import datetime
import random
from urllib.parse import quote
import base64

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

    def create_subscription_for_server(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int, custom_remark: str = None):
        inbounds_list_raw = self.db_manager.get_server_inbounds(server_id, only_active=True)
        if not inbounds_list_raw: return None, None
        server_data = self.db_manager.get_server_by_id(server_id)
        inbounds_to_create = [{'inbound_id': i['inbound_id'], 'server': server_data} for i in inbounds_list_raw]
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
                    "id": client_uuid, "email": unique_email, "totalGB": total_traffic_bytes,
                    "expiryTime": expiry_time_ms, "enable": True, "tgId": str(user_telegram_id),
                    "subId": shared_sub_id, "flow": flow
                }
                
                add_client_payload = {"id": inbound_id, "settings": json.dumps({"clients": [client_settings]})}
                if not api_client.add_client(add_client_payload):
                    logger.error(f"Failed to add client to inbound {inbound_id} on server {server_id}.")
                    continue

                generated_uuids.append(client_uuid)
                single_config = self._generate_single_config_url(client_uuid, server_data, inbound_details, remark_base)
                if single_config: all_generated_configs.append(single_config)

        client_details_for_db = {'uuids': generated_uuids, 'email': base_client_email, 'sub_id': shared_sub_id}
        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)

    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        این تابع به صورت هوشمند و پویا لینک کانفیگ را بر اساس تنظیمات اینباند می‌سازد.
        """
        try:
            protocol = inbound_details.get('protocol')
            if protocol not in ['vless', 'vmess']:
                logger.warning(f"Unsupported protocol for config generation: {protocol}")
                return None

            remark = f"{remark_prefix}-{inbound_details.get('remark', server_data['name'])}"
            address = server_data['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')

            stream_settings_str = inbound_details.get('streamSettings', '{}')
            protocol_settings_str = inbound_details.get('settings', '{}')
            
            stream_settings = json.loads(stream_settings_str) if isinstance(stream_settings_str, str) else stream_settings_str
            protocol_settings = json.loads(protocol_settings_str) if isinstance(protocol_settings_str, str) else protocol_settings_str
            
            # --- استخراج هوشمند پارامترها ---
            params = {}
            
            # ۱. پارامترهای حمل و نقل (Transport)
            network = stream_settings.get('network', 'tcp')
            params['type'] = network
            
            transport_settings = stream_settings.get(f"{network}Settings", {})
            if 'path' in transport_settings:
                params['path'] = transport_settings['path']

            ws_headers = transport_settings.get('headers', {})
            if 'Host' in ws_headers and ws_headers['Host']:
                params['host'] = ws_headers['Host']
            elif 'host' in transport_settings and transport_settings['host']:
                params['host'] = transport_settings['host']

            if 'serviceName' in transport_settings: # برای gRPC
                params['serviceName'] = transport_settings['serviceName']
            
            # ۲. پارامترهای امنیتی (Security)
            security = stream_settings.get('security', 'none')
            if security != 'none':
                params['security'] = security
                security_settings = stream_settings.get(f"{security}Settings", {})
                
                if security_settings.get('serverName'):
                    params['sni'] = security_settings['serverName']
                
                # پارامترهای Reality
                if security == 'reality':
                    nested_reality_settings = security_settings.get('settings', {})
                    if security_settings.get('publicKey'):
                        params['pbk'] = security_settings.get('publicKey')
                    elif nested_reality_settings.get('publicKey'):
                        params['pbk'] = nested_reality_settings.get('publicKey')

                    if security_settings.get('fingerprint'):
                        params['fp'] = security_settings['fingerprint']
                    elif nested_reality_settings.get('fingerprint'):
                        params['fp'] = nested_reality_settings.get('fingerprint')

                    if security_settings.get('shortIds'):
                        valid_sids = [sid for sid in security_settings['shortIds'] if sid]
                        if valid_sids:
                            params['sid'] = random.choice(valid_sids)
                    
                    if security_settings.get('spiderX'):
                        params['spiderX'] = security_settings.get('spiderX')
                    elif nested_reality_settings.get('spiderX'):
                        params['spiderX'] = nested_reality_settings.get('spiderX')
                
                # پارامترهای TLS
                elif security == 'tls':
                    nested_tls_settings = security_settings.get('settings', {})
                    if security_settings.get('fingerprint'):
                         params['fp'] = security_settings.get('fingerprint')
                    elif nested_tls_settings.get('fingerprint'):
                        params['fp'] = nested_tls_settings.get('fingerprint')


            # ۳. ساخت لینک نهایی
            if protocol == 'vless':
                try:
                    flow = protocol_settings.get('clients', [{}])[0].get('flow', '')
                    if flow:
                        params['flow'] = flow
                except (IndexError, TypeError):
                    pass
                
                query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v or v == 0])
                return f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"

            elif protocol == 'vmess':
                try:
                    vmess_client = protocol_settings.get('clients', [{}])[0]
                    vmess_data = {
                        "v": "2", "ps": remark, "add": address, "port": str(port), "id": client_uuid,
                        "aid": str(vmess_client.get("alterId", 0)), "net": network, "type": "none",
                        "host": params.get('host', ''), "path": params.get('path', ''), "tls": security if security != 'none' else ""
                    }
                    if network == 'grpc':
                         vmess_data['path'] = params.get('serviceName','')

                    json_str = json.dumps(vmess_data, separators=(',', ':'))
                    return f"vmess://{base64.b64encode(json_str.encode('utf-8')).decode('utf-8')}"
                except (IndexError, TypeError):
                    return None

        except Exception as e:
            logger.error(f"Error in _generate_single_config_url for inbound {inbound_details.get('id')}: {e}", exc_info=True)
            return None