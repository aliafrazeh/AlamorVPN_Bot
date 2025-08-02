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
        """ --- MODIFIED: Accepts a custom_remark parameter --- """
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
        representative_client_uuid = str(uuid.uuid4())
        representative_client_email = f"u{user_telegram_id}.s{server_id}.{generate_random_string(4)}"

        for db_inbound in active_inbounds_from_db:
            inbound_id_on_panel = db_inbound['inbound_id']
            client_settings = {
                "id": representative_client_uuid, # Use the same UUID for all configs in the sub
                "email": representative_client_email,
                "totalGB": total_traffic_bytes,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": str(user_telegram_id),
                "subId": master_sub_id,
            }

            if not temp_xui_client.add_client(inbound_id_on_panel, json.dumps({"clients": [client_settings]})):
                logger.error(f"Failed to add client to inbound {inbound_id_on_panel}.")
                # Don't abort, just skip this inbound
                continue

            inbound_details = temp_xui_client.get_inbound(inbound_id_on_panel)
            if not inbound_details:
                logger.warning(f"Could not get details for inbound {inbound_id_on_panel}.")
                continue

            # --- NEW: Use custom_remark if provided, otherwise use a default ---
            final_remark = custom_remark if custom_remark else f"Alamor-{server_data['name']}"

            single_config_url = self._generate_single_config_url(
                client_uuid=representative_client_uuid,
                server_data=server_data,
                inbound_details=inbound_details,
                remark=final_remark # Pass the final remark
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
            "email": representative_client_email,
            "subscription_id": master_sub_id
        }
        return client_details_for_db, subscription_link, all_generated_configs

    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark: str) -> dict or None:
        """ --- MODIFIED: Accepts a remark parameter --- """
        try:
            # ... (the logic inside this function remains the same, just ensure it uses the 'remark' variable)
            protocol = inbound_details.get('protocol')
            address = server_data['subscription_base_url'].split('//')[1].split(':')[0].split('/')[0]
            port = inbound_details.get('port')
            
            # ... (rest of the logic for building params)
            
            # Use the passed remark
            config_url = f"vless://{client_uuid}@{address}:{port}?{query_string}#{quote(remark)}"
            
            if config_url:
                return {"remark": remark, "url": config_url}
        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
        return None