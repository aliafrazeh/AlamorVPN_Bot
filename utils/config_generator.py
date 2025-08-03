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
        """ --- MODIFIED: No longer creates single configs --- """
        logger.info(f"Starting config generation for user:{user_telegram_id} on server:{server_id}")
        server_data = self.db_manager.get_server_by_id(server_id)
        if not server_data:
            return None, None # Modified return

        temp_xui_client = self.xui_api(
            panel_url=server_data['panel_url'],
            username=server_data['username'],
            password=server_data['password']
        )
        if not temp_xui_client.login():
            return None, None # Modified return

        master_sub_id = generate_random_string(12)
        # ... (expiry and traffic logic remains the same)

        active_inbounds_from_db = self.db_manager.get_server_inbounds(server_id, only_active=True)
        if not active_inbounds_from_db:
            return None, None # Modified return

        representative_client_uuid = str(uuid.uuid4())
        
        for db_inbound in active_inbounds_from_db:
            inbound_id_on_panel = db_inbound['inbound_id']
            unique_client_email = f"u{user_telegram_id}.i{inbound_id_on_panel}.{generate_random_string(4)}"
            
            client_settings = {
                "id": representative_client_uuid,
                "email": unique_client_email,
                # ... (rest of client_settings)
            }

            add_client_payload = {
                "id": inbound_id_on_panel,
                "settings": json.dumps({"clients": [client_settings]})
            }
            
            if not temp_xui_client.add_client(add_client_payload):
                logger.error(f"Failed to add client to inbound {inbound_id_on_panel}.")
                # If one fails, we should probably stop and return an error
                return None, None

        sub_base_url = server_data['subscription_base_url'].rstrip('/')
        sub_path = server_data['subscription_path_prefix'].strip('/')
        subscription_link = f"{sub_base_url}/{sub_path}/{master_sub_id}"

        client_details_for_db = {
            "uuid": representative_client_uuid,
            "email": f"u{user_telegram_id}.s{server_id}.{generate_random_string(4)}",
            "subscription_id": master_sub_id
        }
        # --- MODIFIED: Return only client_details and the subscription link ---
        return client_details_for_db, subscription_link

    