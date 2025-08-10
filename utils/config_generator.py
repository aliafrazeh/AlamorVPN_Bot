# utils/config_generator.py (نسخه نهایی با معماری دریافت از ساب پنل)

import json
import logging
import uuid
import datetime
import requests
import base64
from urllib.parse import quote, urlunparse

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
        inbounds = self.db_manager.get_active_inbounds_for_server(server_id) # Simplified call
        return self._build_configs(user_telegram_id, inbounds, total_gb, duration_days, custom_remark)

    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        all_final_configs, all_generated_uuids = [], []
        base_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        
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

            for s_inbound in inbounds_on_server:
                inbound_id = s_inbound['inbound_id']
                
                inbound_details = api_client.get_inbound(inbound_id)
                if not inbound_details:
                    logger.warning(f"Could not get details for inbound {inbound_id}. Skipping config generation.")
                    continue

                client_uuid = str(uuid.uuid4())
                flow = ""
                try:
                    clients_settings = json.loads(inbound_details.get('settings', '{}')).get('clients', [{}])
                    flow = clients_settings[0].get('flow', '') if clients_settings else ''
                except Exception: pass

                client_settings = {
                    "id": client_uuid, "email": f"in{inbound_id}.{base_client_email}",
                    "totalGB": total_traffic_bytes, "expiryTime": expiry_time_ms,
                    "enable": True, "flow": flow, "tgId": str(user_telegram_id)
                }
                
                add_client_payload = {"id": inbound_id, "settings": json.dumps({"clients": [client_settings]})}
                if api_client.add_client(add_client_payload):
                    all_generated_uuids.append(client_uuid)
                    remark_prefix = custom_remark or f"AlamorBot-{user_telegram_id}"
                    final_config = self._generate_single_config_url(client_uuid, server_data, inbound_details, remark_prefix)
                    if final_config:
                        all_final_configs.append(final_config)
                else:
                    logger.error(f"Failed to add client to inbound {inbound_id} on server {server_id}.")

        client_details_for_db = {'uuids': all_generated_uuids, 'email': base_client_email}
        return (all_final_configs, client_details_for_db) if all_final_configs else (None, None)
    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        با استفاده از جزئیات کامل اینباند از پنل، لینک کانفیگ را از صفر می‌سازد.
        """
        try:
            protocol = inbound_details.get('protocol')
            if protocol != 'vless': 
                logger.warning(f"Protocol '{protocol}' not supported for generation, skipping.")
                return None

            remark = f"{remark_prefix}-{inbound_details.get('remark', '')}"
            # آدرس را از subscription_base_url سرور می‌خوانیم
            address = server_data['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')

            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            protocol_settings = json.loads(inbound_details.get('settings', '{}'))
            
            params = {}
            network = stream_settings.get('network', 'tcp')
            params['type'] = network
            
            transport_settings = stream_settings.get(f"{network}Settings", {})
            if transport_settings.get('path'): params['path'] = transport_settings.get('path')
            
            ws_headers = transport_settings.get('headers', {})
            if ws_headers.get('Host'): params['host'] = ws_headers.get('Host')
            elif transport_settings.get('host'): params['host'] = transport_settings.get('host')

            if transport_settings.get('serviceName'): params['serviceName'] = transport_settings.get('serviceName')
            
            security = stream_settings.get('security', 'none')
            if security != 'none':
                params['security'] = security
                security_settings = stream_settings.get(f"{security}Settings", {})
                
                if security_settings.get('fingerprint'): params['fp'] = security_settings.get('fingerprint')
                elif 'settings' in security_settings and security_settings['settings'].get('fingerprint'): params['fp'] = security_settings['settings']['fingerprint']

                if security == 'tls':
                    if security_settings.get('serverName'): params['sni'] = security_settings.get('serverName')
                    if security_settings.get('alpn'): params['alpn'] = ','.join(security_settings.get('alpn', []))
                
                elif security == 'reality':
                    nested_reality_settings = security_settings.get('settings', {})
                    if security_settings.get('serverNames'):
                        valid_snis = [s for s in security_settings['serverNames'] if s]
                        if valid_snis: params['sni'] = valid_snis[0]
                    if security_settings.get('publicKey'): params['pbk'] = security_settings.get('publicKey')
                    elif nested_reality_settings.get('publicKey'): params['pbk'] = nested_reality_settings.get('publicKey')
                    if security_settings.get('shortIds'):
                        valid_sids = [s for s in security_settings['shortIds'] if s]
                        if valid_sids: params['sid'] = valid_sids[0]
                    if security_settings.get('spiderX'): params['spiderX'] = security_settings.get('spiderX')
                    elif nested_reality_settings.get('spiderX'): params['spiderX'] = nested_reality_settings.get('spiderX')

            flow = protocol_settings.get('clients', [{}])[0].get('flow', '')
            if flow: params['flow'] = flow

            query_string = '&'.join([f"{key}={quote(str(value))}" for key, value in params.items() if value is not None and key != 'path'])
            
            netloc = f"{client_uuid}@{address}:{port}"
            url_parts = ('vless', netloc, params.get('path','/'), '', query_string, quote(remark))
            
            return urlunparse(url_parts)
        except Exception as e:
            logger.error(f"Error building config from scratch for inbound {inbound_details.get('id')}: {e}", exc_info=True)
            return None

