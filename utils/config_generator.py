# utils/config_generator.py

import json
import logging
import uuid
import datetime
from urllib.parse import quote

from utils.helpers import generate_random_string

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self, xui_api_client, db_manager):
        self.xui_api = xui_api_client
        self.db_manager = db_manager

    def create_client_and_configs(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int or None, custom_remark: str = None):
        """MODIFIED: Generates a unique email for each inbound to prevent conflicts."""
        logger.info(f"Starting config generation for user:{user_telegram_id} on server:{server_id}")
        server_data = self.db_manager.get_server_by_id(server_id)
        if not server_data:
            logger.error(f"Server {server_id} not found.")
            return None, None, None

        temp_xui_client = self.xui_api(
            panel_url=server_data['panel_url'],
            username=server_data['username'],
            password=server_data['password']
        )
        if not temp_xui_client.login():
            logger.error(f"Failed to login to X-UI panel for server {server_data['name']}.")
            return None, None, None

        master_sub_id = generate_random_string(12)
        expiry_time_ms = 0
        if duration_days is not None and duration_days > 0:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
            expiry_time_ms = int(expire_date.timestamp() * 1000)
        
        total_traffic_bytes = int(total_gb * (1024**3)) if total_gb is not None else 0

        active_inbounds_from_db = self.db_manager.get_server_inbounds(server_id, only_active=True)
        if not active_inbounds_from_db:
            logger.error(f"No active inbounds configured for server {server_id}.")
            return None, None, None

        all_generated_configs = []
        # This UUID is shared across all inbounds for the subscription to work correctly
        representative_client_uuid = str(uuid.uuid4())
        
        for db_inbound in active_inbounds_from_db:
            inbound_id_on_panel = db_inbound['inbound_id']
            
            # --- THE FIX IS HERE ---
            # Generate a NEW, unique email for each inbound to avoid panel conflicts
            unique_client_email = f"u{user_telegram_id}.i{inbound_id_on_panel}.{generate_random_string(4)}"
            
            client_settings = {
                "id": representative_client_uuid, # UUID must be the same
                "email": unique_client_email,      # Email must be unique
                "totalGB": total_traffic_bytes,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": str(user_telegram_id),
                "subId": master_sub_id,
            }

            add_client_payload = {
                "id": inbound_id_on_panel,
                "settings": json.dumps({"clients": [client_settings]})
            }
            
            if not temp_xui_client.add_client(add_client_payload):
                logger.error(f"Failed to add client to inbound {inbound_id_on_panel}.")
                continue
            # --- END OF FIX ---

            inbound_details = temp_xui_client.get_inbound(inbound_id_on_panel)
            if not inbound_details:
                logger.warning(f"Could not get details for inbound {inbound_id_on_panel}.")
                continue

            final_remark = custom_remark if custom_remark else f"Alamor-{server_data['name']}"
            single_config_url = self._generate_single_config_url(
                client_uuid=representative_client_uuid,
                server_data=server_data,
                inbound_details=inbound_details,
                remark=final_remark
            )
            if single_config_url:
                all_generated_configs.append(single_config_url)
        
        if not all_generated_configs:
            logger.error("Failed to generate any valid configs.")
            return None, None, None

        sub_base_url = server_data['subscription_base_url'].rstrip('/')
        sub_path = server_data['subscription_path_prefix'].strip('/')
        subscription_link = f"{sub_base_url}/{sub_path}/{master_sub_id}"

        client_details_for_db = {
            "uuid": representative_client_uuid,
            # We store one of the generated emails for reference; it doesn't matter which one
            "email": f"u{user_telegram_id}.s{server_id}.{generate_random_string(4)}",
            "subscription_id": master_sub_id
        }
        return client_details_for_db, subscription_link, all_generated_configs

    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark: str) -> dict or None:
        """ --- MODIFIED: Safely handles empty serverNames for REALITY --- """
        try:
            protocol = inbound_details.get('protocol')
            address = server_data['subscription_base_url'].split('//')[1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')
            
            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            network = stream_settings.get('network', 'tcp')
            security = stream_settings.get('security', 'none')
            
            config_url = ""
            params = {'type': network}

            if protocol == 'vless':
                if security in ['tls', 'xtls', 'reality']:
                    params['security'] = security
                
                if security == 'reality':
                    reality_settings = stream_settings.get('realitySettings', {})
                    params['fp'] = reality_settings.get('fingerprint', '')
                    params['pbk'] = reality_settings.get('publicKey', '')
                    params['sid'] = reality_settings.get('shortId', '')
                    
                    # --- THE FIX IS HERE ---
                    # Safely get the SNI from the serverNames list
                    server_names = reality_settings.get('serverNames', [])
                    if server_names: # Check if the list is not empty
                        params['sni'] = server_names[0]
                    # --- END OF FIX ---

                if security == 'tls':
                    tls_settings = stream_settings.get('tlsSettings', {})
                    params['sni'] = tls_settings.get('serverName', address)

                if network == 'ws':
                    ws_settings = stream_settings.get('wsSettings', {})
                    params['path'] = ws_settings.get('path', '/')
                    params['host'] = ws_settings.get('headers', {}).get('Host', address)
                    if security == 'tls':
                        params['sni'] = params['host']

                if security == 'xtls':
                    xtls_settings = stream_settings.get('xtlsSettings', {})
                    params['flow'] = xtls_settings.get('flow', 'xtls-rprx-direct')

                query_string = '&'.join([f"{key}={quote(str(value))}" for key, value in params.items() if value])
                
                config_url = f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"
                
                if config_url:
                    return {"remark": remark, "url": config_url}

        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
        return None