# utils/config_generator.py

# --- NEW: Import the API factory ---
from api_client.factory import get_api_client
import datetime
import json
from utils.helpers import generate_random_string
import logging

logger = logging.getLogger(__name__)


class ConfigGenerator:
    def __init__(self, xui_api_client, db_manager):
        self.xui_api = xui_api_client # This is kept for legacy compatibility if needed elsewhere
        self.db_manager = db_manager

    def create_client_and_configs(self, user_telegram_id: int, server_id: int, total_gb: float, duration_days: int or None, custom_remark: str = None):
        """
        --- FINAL & ROBUST VERSION ---
        This version now uses the API factory to work with any panel type.
        """
        logger.info(f"Starting config generation for user:{user_telegram_id} on server:{server_id}")
        server_data = self.db_manager.get_server_by_id(server_id)
        if not server_data:
            logger.error(f"Server {server_id} not found.")
            return None, None

        # --- THE FIX IS HERE: Use the factory to get the correct API client ---
        api_client = get_api_client(server_data)
        if not api_client:
            logger.error(f"Could not initialize API client for server {server_id} with panel type {server_data.get('panel_type')}.")
            return None, None
        
        # The login check is now handled by the API client itself
        if not api_client.check_login():
             logger.error(f"Failed to login to panel for server {server_data['name']}.")
             return None, None

        # --- The rest of the function logic ---
        master_sub_id = generate_random_string(12)
        expiry_time_ms = 0
        if duration_days is not None and duration_days > 0:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
            expiry_time_ms = int(expire_date.timestamp() * 1000)
        total_traffic_bytes = int(total_gb * (1024**3)) if total_gb is not None else 0

        active_inbounds_from_db = self.db_manager.get_server_inbounds(server_id, only_active=True)
        if not active_inbounds_from_db:
            logger.error(f"No active inbounds configured for server {server_id}.")
            return None, None

        representative_client_uuid = str(uuid.uuid4())
        at_least_one_client_created = False

        for db_inbound in active_inbounds_from_db:
            inbound_id_on_panel = db_inbound['inbound_id']
            unique_client_email = f"u{user_telegram_id}.i{inbound_id_on_panel}.{generate_random_string(4)}"
            
            client_settings = {
                "id": representative_client_uuid,
                "email": unique_client_email,
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
            
            if api_client.add_client(add_client_payload):
                at_least_one_client_created = True
            else:
                logger.error(f"Could not add client to inbound {inbound_id_on_panel}. Skipping.")

        if not at_least_one_client_created:
            logger.error(f"Failed to create any clients on the panel for user {user_telegram_id}. Aborting.")
            return None, None

        sub_base_url = server_data['subscription_base_url'].rstrip('/')
        sub_path = server_data['subscription_path_prefix'].strip('/')
        subscription_link = f"{sub_base_url}/{sub_path}/{master_sub_id}"

        client_details_for_db = {
            "uuid": representative_client_uuid,
            "email": f"u{user_telegram_id}.s{server_id}.{generate_random_string(4)}",
            "subscription_id": master_sub_id
        }
        return client_details_for_db, subscription_link