# utils/config_generator.py

# --- NEW: Import the API factory ---
from api_client.factory import get_api_client
import uuid
import datetime
import json
import logging
from .helpers import generate_random_string

logger = logging.getLogger(__name__)


class ConfigGenerator:
    def __init__(self, xui_api_client, db_manager):
        # This class no longer needs xui_api_client, but we keep it for backward compatibility
        self.db_manager = db_manager
        logger.info("ConfigGenerator initialized.")

    def create_subscription_for_profile(self, user_telegram_id: int, profile_id: int, total_gb: float, custom_remark: str = None):
        """کانفیگ‌های یک پروفایل را بر اساس اینباندهای تعریف شده برای آن می‌سازد."""
        profile_details = self.db_manager.get_profile_by_id(profile_id)
        if not profile_details:
            return None, None
        
        # دریافت لیست اینباندها به همراه اطلاعات کامل سرورشان
        inbounds_to_create = self.db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        duration_days = profile_details['duration_days']
        
        return self._build_configs(user_telegram_id, inbounds_to_create, total_gb, duration_days, custom_remark)

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
    
    
    
    def create_configs_for_profile(db_manager, user_telegram_id, profile_id, requested_gb, custom_remark=None):
        """
        برای یک پروفایل، به تمام پنل‌های مربوطه متصل شده، کلاینت‌ها را ساخته
        و لیستی از لینک‌های کانفیگ تکی را برمی‌گرداند.
        """
        logger.info(f"Starting profile config generation for user:{user_telegram_id}, profile:{profile_id}")
        
        profile_details = db_manager.get_profile_by_id(profile_id)
        if not profile_details:
            logger.error(f"Profile {profile_id} not found.")
            return None, None

        profile_inbounds = db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        if not profile_inbounds:
            logger.error(f"No inbounds are defined for profile {profile_id}.")
            return None, None

        total_traffic_bytes = int(requested_gb * (1024**3))
        duration_days = profile_details['duration_days']
        expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
        expiry_time_ms = int(expire_date.timestamp() * 1000)
        
        shared_uuid = str(uuid.uuid4())
        master_sub_id = generate_random_string(12)
        
        generated_configs = []
        
        for inbound_map in profile_inbounds:
            server_data = inbound_map['server']
            inbound_id_on_panel = inbound_map['inbound_id']
            
            api_client = get_api_client(server_data)
            if not api_client or not api_client.check_login():
                logger.warning(f"Could not connect to server {server_data['name']} for profile generation. Skipping.")
                continue

            client_email = f"p{profile_id}.u{user_telegram_id}.{generate_random_string(4)}"
            remark = custom_remark or f"Profile-{profile_details['name']}"
            
            client_settings = {
                "id": shared_uuid,
                "email": client_email,
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
            
            if not api_client.add_client(add_client_payload):
                logger.warning(f"Failed to add client to inbound {inbound_id_on_panel} on server {server_data['name']}. Skipping.")
                continue
                
            inbound_details = api_client.get_inbound(inbound_id_on_panel)
            if not inbound_details:
                logger.warning(f"Could not fetch details for inbound {inbound_id_on_panel} to build config link. Skipping.")
                continue

            try:
                stream_settings = json.loads(inbound_details.get("streamSettings", "{}"))
                final_remark = f"{remark}-{server_data['name']}"
                config_link = (
                    f"vless://{shared_uuid}@{server_data['subscription_base_url']}:{inbound_details['port']}"
                    f"?type={stream_settings.get('network', 'tcp')}"
                    f"&security={stream_settings.get('security', 'none')}"
                    f"#{final_remark}"
                )
                generated_configs.append(config_link)
                logger.info(f"Successfully generated config for user {user_telegram_id} on server {server_data['name']}")
            except Exception as e:
                logger.error(f"Error building config link for inbound {inbound_id_on_panel}: {e}")

        if not generated_configs:
            return None, None
            
        return generated_configs, [shared_uuid]
    
    
    def _generate_single_config_url(self, client_uuid: str, server_data: dict, inbound_details: dict, remark_prefix: str) -> str or None:
        """
        لینک کانفیگ تکی را بر اساس اطلاعات ورودی تولید می‌کند (فرض بر VLESS/TCP).
        """
        try:
            protocol = inbound_details.get('protocol')
            remark = f"{remark_prefix}-{inbound_details.get('remark', server_data['name'])}"
            address = server_data['subscription_base_url']
            port = inbound_details.get('port')
            
            stream_settings = json.loads(inbound_details.get('streamSettings', '{}'))
            network = stream_settings.get('network', 'tcp')
            security = stream_settings.get('security', 'none')
            
            if protocol == 'vless':
                query_params = f"type={network}&security={security}"
                # در آینده می‌توان پارامترهای دیگر (ws, grpc, reality) را نیز اینجا اضافه کرد
                return f"vless://{client_uuid}@{address}:{port}?{query_params}#{quote(remark)}"

        except Exception as e:
            logger.error(f"Error in _generate_single_config_url: {e}")
        return None
    
    
    def _build_configs(self, user_telegram_id: int, inbounds_list: list, total_gb: float, duration_days: int, custom_remark: str = None):
        """
        موتور اصلی ساخت کانفیگ. این تابع به پنل‌ها متصل شده، کلاینت‌ها را ساخته
        و اطلاعات لازم برای ثبت در دیتابیس و ساخت لینک را برمی‌گرداند.
        """
        all_generated_configs = []
        
        # ساخت اطلاعات مشترک برای تمام کانفیگ‌های این خرید
        master_client_uuid = str(uuid.uuid4())
        master_client_email = f"u{user_telegram_id}.{generate_random_string(6)}"
        
        client_details_for_db = {
            'uuid': master_client_uuid, 
            'email': master_client_email
        }

        # دسته‌بندی اینباندها بر اساس سرور برای بهینه‌سازی
        inbounds_by_server = {}
        for inbound_info in inbounds_list:
            server_id = inbound_info['server']['id']
            if server_id not in inbounds_by_server:
                inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(inbound_info)

        # شروع فرآیند ساخت کانفیگ برای هر سرور
        for server_id, inbounds in inbounds_by_server.items():
            server_data = inbounds[0]['server'] # اطلاعات سرور برای همه اینباندها یکسان است
            
            # --- استفاده صحیح از API Factory ---
            api_client = get_api_client(server_data)
            if not api_client or not api_client.check_login():
                logger.error(f"Could not connect to server {server_data['name']} (ID: {server_id}). Skipping.")
                continue

            # دریافت جزئیات تمام اینباندهای روی پنل برای دسترسی سریع
            panel_inbounds_details = {i['id']: i for i in api_client.list_inbounds()}
            if not panel_inbounds_details:
                logger.error(f"Could not retrieve any inbound details from server {server_id}.")
                continue

            # محاسبه تاریخ انقضا و حجم
            expiry_time_ms = 0
            if duration_days and duration_days > 0:
                expire_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
                expiry_time_ms = int(expire_date.timestamp() * 1000)
            
            total_traffic_bytes = int(total_gb * (1024**3)) if total_gb and total_gb > 0 else 0

            for s_inbound in inbounds:
                inbound_id_on_panel = s_inbound['inbound_id']
                
                remark = custom_remark or f"AlamorBot-{user_telegram_id}"

                client_settings = {
                    "id": master_client_uuid, "email": master_client_email,
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
                else:
                    logger.warning(f"Details for inbound ID {inbound_id_on_panel} not found on panel.")

        return (all_generated_configs, client_details_for_db) if all_generated_configs else (None, None)
    
   