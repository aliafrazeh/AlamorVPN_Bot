# webhook_server.py (نسخه نهایی با سرور اشتراک و منطق تفکیک خرید)

from flask import Flask, request, render_template, Response
import requests
import json
import logging
import os
import sys
import datetime
import base64
import telebot
from urllib.parse import quote
from utils import messages

# افزودن مسیر پروژه به sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# وارد کردن ماژول‌های پروژه
from config import BOT_TOKEN, BOT_USERNAME_ALAMOR
from database.db_manager import DatabaseManager
from utils.bot_helpers import send_subscription_info, finalize_profile_purchase
from utils.config_generator import ConfigGenerator
from api_client.xui_api_client import XuiAPIClient # برای خرید عادی

# تنظیمات اولیه
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
db_manager = DatabaseManager()
bot = telebot.TeleBot(BOT_TOKEN)
# یک نمونه از کانفیگ جنریتور برای خرید عادی
config_gen_normal = ConfigGenerator(db_manager)

ZARINPAL_VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
BOT_USERNAME = BOT_USERNAME_ALAMOR

# --- تابع کمکی برای ساخت کانفیگ ---
def build_config_link(synced_config, client_uuid, client_remark):
    """
    با استفاده از اطلاعات خام همگام‌سازی شده و آدرس اصلی سرور، لینک کانفیگ نهایی را می‌سازد.
    """
    try:
        # --- اصلاح اصلی اینجاست ---
        # آدرس را از اطلاعات خود کانفیگ می‌خوانیم، نه از دامنه ضد فیلتر
        server_address = synced_config['subscription_base_url'].split('//')[-1].split(':')[0].split('/')[0]
        
        port = synced_config['port']
        remark = f"{client_remark} - {synced_config['remark']}"
        
        if synced_config['protocol'] == 'vless':
            stream_settings = json.loads(synced_config['stream_settings'])
            protocol_settings = json.loads(synced_config['settings'])
            
            params = {
                'type': stream_settings.get('network', 'tcp'),
                'security': stream_settings.get('security', 'none')
            }

            flow = protocol_settings.get('clients', [{}])[0].get('flow', '')
            if flow:
                params['flow'] = flow

            if params['security'] == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                nested_tls_settings = tls_settings.get('settings', {})
                params['fp'] = nested_tls_settings.get('fingerprint', '')
                params['sni'] = tls_settings.get('serverName', server_address)

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

            if params['type'] == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                params['path'] = ws_settings.get('path', '')
                params['host'] = ws_settings.get('host', '')
            
            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v])
            
            # --- استفاده از server_address به جای active_domain ---
            return f"vless://{client_uuid}@{server_address}:{port}?{query_string}#{quote(remark)}"
            
    except Exception as e:
        logger.error(f"Error building config link for inbound {synced_config.get('inbound_id')}: {e}")
        return None

def process_subscription_content(content):
    """
    پردازش محتوای subscription و تشخیص نوع آن
    """
    try:
        if not content:
            logger.error("Content is empty or None")
            return None
            
        # تلاش برای decode کردن Base64
        decoded_content = base64.b64decode(content).decode('utf-8')
        # اگر موفق شد، محتوا Base64 بوده
        return {
            'is_base64': True,
            'original': content,
            'decoded': decoded_content,
            'final': content  # همان Base64 را برمی‌گردانیم
        }
    except Exception as e:
        # اگر decode نشد، محتوا عادی است
        try:
            return {
                'is_base64': False,
                'original': content,
                'decoded': content,
                'final': base64.b64encode(content.encode('utf-8')).decode('utf-8')  # encode می‌کنیم
            }
        except Exception as encode_error:
            logger.error(f"Error processing subscription content: {e}, encode error: {encode_error}")
            return None

def detect_content_type(content):
    """
    تشخیص نوع محتوای subscription
    """
    # بررسی اینکه آیا محتوا Base64 است
    try:
        decoded = base64.b64decode(content)
        # اگر موفق شد، احتمالاً Base64 است
        return 'base64'
    except:
        pass
    
    # بررسی اینکه آیا محتوا JSON است
    try:
        json.loads(content)
        return 'json'
    except:
        pass
    
    # بررسی اینکه آیا محتوا V2Ray config است
    if 'vmess://' in content or 'vless://' in content or 'trojan://' in content:
        return 'v2ray_config'
    
    # پیش‌فرض: plain text
    return 'plain_text'

def get_panel_subscription_data(server_info, sub_id):
    """
    دریافت دیتای subscription از پنل اصلی
    """
    try:
        # بررسی وجود sub_id
        if not sub_id:
            logger.error(f"sub_id is None or empty for server {server_info.get('id')}")
            return None
            
        # ساخت URL پنل اصلی
        panel_url = server_info.get('panel_url', '').rstrip('/')
        if not panel_url:
            logger.error(f"panel_url is not set for server {server_info.get('id')}")
            return None
            
        subscription_path = server_info.get('subscription_path_prefix', '').strip('/')
        
        # URL نهایی برای دریافت subscription
        if subscription_path:
            subscription_url = f"{panel_url}/{subscription_path}/{sub_id}"
        else:
            subscription_url = f"{panel_url}/{sub_id}"
        
        logger.info(f"📡 Panel Request Details:")
        logger.info(f"   Server ID: {server_info.get('id')}")
        logger.info(f"   Server Name: {server_info.get('name')}")
        logger.info(f"   Panel URL: {panel_url}")
        logger.info(f"   Subscription Path: {subscription_path}")
        logger.info(f"   Sub ID: {sub_id}")
        logger.info(f"   Final URL: {subscription_url}")
        
        # درخواست GET به پنل اصلی
        response = requests.get(subscription_url, verify=False, timeout=30)
        response.raise_for_status()
        
        # بررسی نوع محتوا
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            # اگر JSON است، احتمالاً encode شده
            try:
                json_data = response.json()
                if isinstance(json_data, dict) and 'data' in json_data:
                    # احتمالاً Base64 encoded
                    import base64
                    decoded_data = base64.b64decode(json_data['data']).decode('utf-8')
                    return decoded_data
                else:
                    # JSON عادی
                    return response.text
            except Exception as json_error:
                logger.warning(f"JSON parsing failed, returning raw text: {json_error}")
                return response.text
        else:
            # محتوای عادی (مثل Base64 یا plain text)
            return response.text
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching subscription data from panel: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_panel_subscription_data: {e}")
        return None

def get_webhook_subscription_data(purchase):
    """
    دریافت دیتای subscription از webhook server فعلی (بهترین روش)
    """
    try:
        sub_id = purchase.get('sub_id')
        if not sub_id:
            logger.error(f"Purchase {purchase['id']} has no sub_id")
            return None
        
        # دریافت دامنه فعال از دیتابیس
        active_domain = db_manager.get_setting('active_domain')
        if not active_domain:
            logger.error("No active domain set in database")
            return None
        
        # ساخت URL webhook
        webhook_url = f"https://{active_domain}/sub/{sub_id}"
        logger.info(f"Fetching subscription data from webhook: {webhook_url}")
        
        # درخواست GET به webhook server
        response = requests.get(webhook_url, timeout=30)
        response.raise_for_status()
        
        # محتوای webhook server همیشه plain text است
        return response.text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching subscription data from webhook: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_webhook_subscription_data: {e}")
        return None

def update_cached_configs_from_panel(purchase_id):
    """
    بروزرسانی کانفیگ‌های ذخیره شده از پنل اصلی
    """
    try:
        logger.info(f"Starting update_cached_configs_from_panel for purchase {purchase_id}")
        
        # نمایش اطلاعات دامنه‌ها
        webhook_domain = os.getenv('WEBHOOK_DOMAIN')
        active_domain = db_manager.get_setting('active_domain')
        logger.info(f"🌐 Webhook Domain: {webhook_domain}")
        logger.info(f"🔗 Active Domain (User Subscriptions): {active_domain}")
        
        purchase = db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            logger.error(f"Purchase {purchase_id} not found in database")
            return False
        
        # بررسی وجود sub_id
        if not purchase.get('sub_id'):
            logger.error(f"Purchase {purchase_id} has no sub_id")
            return False
        
        # بررسی وجود server_id برای خریدهای عادی
        if not purchase.get('profile_id') and not purchase.get('server_id'):
            logger.error(f"Purchase {purchase_id} has no server_id and is not a profile purchase")
            return False
        
        # --- منطق جدید: تفکیک خرید پروفایل و عادی ---
        if purchase.get('profile_id'):
            logger.info(f"Processing profile purchase {purchase_id} with profile_id {purchase['profile_id']}")
            # خرید پروفایل: از تمام سرورهای پروفایل دیتا جمع‌آوری کن
            try:
                subscription_data = get_profile_subscription_data(purchase)
            except Exception as e:
                logger.error(f"Error in get_profile_subscription_data for purchase {purchase_id}: {e}")
                # Fallback: try normal purchase method
                logger.info(f"Falling back to normal purchase method for purchase {purchase_id}")
                server = db_manager.get_server_by_id(purchase.get('server_id'))
                if server:
                    subscription_data = get_panel_subscription_data(server, purchase['sub_id'])
                else:
                    subscription_data = None
        else:
            logger.info(f"Processing normal purchase {purchase_id} with server_id {purchase.get('server_id')}")
            # خرید عادی: فقط از سرور انتخاب شده
            server = db_manager.get_server_by_id(purchase['server_id'])
            if not server:
                logger.error(f"Server {purchase['server_id']} for purchase {purchase_id} not found")
                return False
            subscription_data = get_panel_subscription_data(server, purchase['sub_id'])
        
        # اگر نتوانستیم از پنل دیتا بگیریم، از دیتای cached استفاده می‌کنیم
        if not subscription_data:
            logger.warning(f"⚠️ Could not fetch subscription data from panel for purchase {purchase_id}, using cached data")
            cached_configs = purchase.get('single_configs_json')
            if cached_configs:
                try:
                    config_list = json.loads(cached_configs)
                    subscription_data = "\n".join(config_list)
                    logger.info(f"✅ Using cached configs for purchase {purchase_id}: {len(config_list)} configs")
                    logger.info(f"   📄 Cached data length: {len(subscription_data)} characters")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"❌ Error parsing cached configs for purchase {purchase_id}: {e}")
                    return False
            else:
                logger.error(f"❌ No cached configs available for purchase {purchase_id}")
                return False
        
        logger.info(f"✅ Successfully fetched subscription data for purchase {purchase_id}")
        logger.info(f"   📄 Data length: {len(subscription_data)} characters")
        logger.info(f"   📊 Data source: {'Panel' if 'panel' in str(subscription_data) else 'Cached'}")
        
        # پردازش محتوا
        processed_content = process_subscription_content(subscription_data)
        if not processed_content:
            logger.error(f"❌ Failed to process subscription content for purchase {purchase_id}")
            return False
        
        # اگر محتوا Base64 است، آن را decode کنیم
        if processed_content.get('is_base64'):
            config_content = processed_content.get('decoded', '')
            logger.info(f"   🔓 Content type: Base64 (decoded)")
        else:
            config_content = processed_content.get('original', '')
            logger.info(f"   📝 Content type: Plain text")
        
        if not config_content:
            logger.error(f"❌ No config content available for purchase {purchase_id}")
            return False
        
        # تقسیم کانفیگ‌ها بر اساس خط جدید
        config_list = config_content.strip().split('\n')
        
        # فیلتر کردن خطوط خالی
        config_list = [config for config in config_list if config.strip()]
        
        if not config_list:
            logger.error(f"❌ No valid configs found for purchase {purchase_id}")
            return False
        
        logger.info(f"✅ Found {len(config_list)} valid configs for purchase {purchase_id}")
        logger.info(f"   📋 Config types: {', '.join(set([config.split('://')[0] for config in config_list if '://' in config]))}")
        
        # ذخیره در دیتابیس
        logger.info(f"💾 Saving configs to database for purchase {purchase_id}")
        success = db_manager.update_purchase_configs(purchase_id, json.dumps(config_list))
        
        if success:
            logger.info(f"✅ Successfully updated cached configs for purchase {purchase_id}")
            logger.info(f"   📊 Summary: {len(config_list)} configs saved to database")
            return True
        else:
            logger.error(f"❌ Failed to update cached configs in database for purchase {purchase_id}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error in update_cached_configs_from_panel for purchase {purchase_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

# --- Endpoint جدید برای سرور اشتراک ---
@app.route('/sub/<sub_id>', methods=['GET'])
def serve_subscription(sub_id):
    logger.info(f"Subscription request received for sub_id: {sub_id}")
    
    purchase = db_manager.get_purchase_by_sub_id(sub_id)
    if not purchase or not purchase['is_active']:
        return Response("Subscription not found or is inactive.", status=404)
    
    # --- منطق جدید: تفکیک خرید پروفایل و عادی ---
    if purchase.get('profile_id'):
        # خرید پروفایل: از تمام سرورهای پروفایل دیتا جمع‌آوری کن
        subscription_data = get_profile_subscription_data(purchase)
    else:
        # خرید عادی: فقط از سرور انتخاب شده
        subscription_data = get_normal_subscription_data(purchase)
    
    if not subscription_data:
        # اگر نتوانستیم از پنل اصلی دریافت کنیم، از دیتابیس استفاده می‌کنیم
        logger.warning(f"Could not fetch from panel, using cached data for sub_id: {sub_id}")
        single_configs_str = purchase.get('single_configs_json')
        if not single_configs_str:
            return Response("No configurations found for this subscription.", status=404)

        try:
            config_list = json.loads(single_configs_str)
            subscription_data = "\n".join(config_list)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error processing cached subscription for sub_id {sub_id}: {e}")
            return Response("Error processing subscription data.", status=500)
    
    # پردازش محتوای subscription
    processed_content = process_subscription_content(subscription_data)
    content_type = detect_content_type(subscription_data)
    
    logger.info(f"Subscription content type: {content_type}, is_base64: {processed_content['is_base64']}")
    
    return Response(processed_content['final'], mimetype='text/plain')

def get_profile_subscription_data(purchase):
    """
    دریافت دیتای subscription برای خرید پروفایل از تمام سرورهای مرتبط
    """
    try:
        profile_id = purchase.get('profile_id')
        if not profile_id:
            logger.error(f"Purchase {purchase['id']} has no profile_id")
            return None
        
        logger.info(f"Getting profile subscription data for profile_id: {profile_id}")
        
        # دریافت تمام اینباندهای پروفایل از تمام سرورها
        profile_inbounds = db_manager.get_inbounds_for_profile(profile_id, with_server_info=True)
        if not profile_inbounds:
            logger.error(f"No inbounds found for profile {profile_id}")
            return None
        
        logger.info(f"📋 Profile Details:")
        logger.info(f"   Profile ID: {profile_id}")
        logger.info(f"   Total Inbounds: {len(profile_inbounds)}")
        logger.info(f"   Sub ID: {sub_id}")
        
        # نمایش جزئیات سرورها
        servers_info = {}
        for inbound in profile_inbounds:
            server_id = inbound['server']['id']
            server_name = inbound['server']['name']
            if server_id not in servers_info:
                servers_info[server_id] = {
                    'name': server_name,
                    'inbounds': 0
                }
            servers_info[server_id]['inbounds'] += 1
        
        logger.info(f"   Servers involved:")
        for server_id, info in servers_info.items():
            logger.info(f"     - Server {server_id}: {info['name']} ({info['inbounds']} inbounds)")
        
        all_configs = []
        sub_id = purchase.get('sub_id')
        
        if not sub_id:
            logger.error(f"Purchase {purchase['id']} has no sub_id")
            return None
        
        # گروه‌بندی اینباندها بر اساس سرور
        inbounds_by_server = {}
        for inbound_info in profile_inbounds:
            try:
                server_id = inbound_info['server']['id']
                if server_id not in inbounds_by_server:
                    inbounds_by_server[server_id] = []
                inbounds_by_server[server_id].append(inbound_info)
            except KeyError as e:
                logger.error(f"Missing server info in inbound: {e}")
                continue
        
        if not inbounds_by_server:
            logger.error(f"No valid server information found for profile {profile_id}")
            return None
        
        # دریافت دیتا از هر سرور
        for server_id, server_inbounds in inbounds_by_server.items():
            try:
                server_info = server_inbounds[0]['server']
                logger.info(f"🔄 Processing Server {server_info['name']} (ID: {server_id})")
                logger.info(f"   Inbounds on this server: {len(server_inbounds)}")
                
                # دریافت دیتای subscription از این سرور
                server_subscription_data = get_panel_subscription_data(server_info, sub_id)
                if server_subscription_data:
                    # پردازش و فیلتر کردن کانفیگ‌های مربوط به این سرور
                    processed_configs = process_server_configs(server_subscription_data, server_inbounds)
                    all_configs.extend(processed_configs)
                    logger.info(f"   ✅ Success: Added {len(processed_configs)} configs from server {server_info['name']}")
                else:
                    logger.warning(f"   ⚠️ Warning: Could not fetch data from server {server_info['name']}")
            except Exception as e:
                logger.error(f"   ❌ Error processing server {server_id}: {e}")
                continue
        
        if not all_configs:
            logger.warning(f"No configs collected from any server for profile {profile_id}, trying fallback")
            # Fallback: سعی می‌کنیم از دیتای cached استفاده کنیم
            cached_configs = purchase.get('single_configs_json')
            if cached_configs:
                try:
                    config_list = json.loads(cached_configs)
                    final_subscription_data = "\n".join(config_list)
                    logger.info(f"Using cached configs for profile {profile_id}: {len(config_list)} configs")
                    return final_subscription_data
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error parsing cached configs for profile {profile_id}: {e}")
                    return None
            else:
                logger.error(f"No cached configs available for profile {profile_id}")
                return None
        
        # ترکیب تمام کانفیگ‌ها
        final_subscription_data = "\n".join(all_configs)
        logger.info(f"Total configs collected for profile {profile_id}: {len(all_configs)}")
        
        return final_subscription_data
        
    except Exception as e:
        logger.error(f"Error in get_profile_subscription_data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def get_normal_subscription_data(purchase):
    """
    دریافت دیتای subscription برای خرید عادی (فقط از یک سرور)
    """
    try:
        server = db_manager.get_server_by_id(purchase['server_id'])
        if not server:
            logger.error(f"Server for purchase {purchase['id']} not found")
            return None
        
        sub_id = purchase.get('sub_id')
        return get_panel_subscription_data(server, sub_id)
        
    except Exception as e:
        logger.error(f"Error in get_normal_subscription_data: {e}")
        return None

def process_server_configs(subscription_data, server_inbounds):
    """
    پردازش کانفیگ‌های یک سرور و فیلتر کردن کانفیگ‌های مربوط به اینباندهای پروفایل
    """
    try:
        # پردازش محتوای subscription
        processed_content = process_subscription_content(subscription_data)
        if not processed_content:
            return []
        
        # اگر محتوا Base64 است، آن را decode کنیم
        if processed_content.get('is_base64'):
            config_content = processed_content.get('decoded', '')
        else:
            config_content = processed_content.get('original', '')
        
        if not config_content:
            return []
        
        # تقسیم کانفیگ‌ها بر اساس خط جدید
        config_list = config_content.strip().split('\n')
        
        # فیلتر کردن خطوط خالی
        config_list = [config for config in config_list if config.strip()]
        
        # فیلتر کردن کانفیگ‌های مربوط به اینباندهای پروفایل
        # این کار بر اساس remark یا سایر شناسه‌های اینباند انجام می‌شود
        filtered_configs = []
        
        for config in config_list:
            # بررسی اینکه آیا این کانفیگ مربوط به یکی از اینباندهای پروفایل است
            if is_config_for_profile_inbounds(config, server_inbounds):
                filtered_configs.append(config)
        
        return filtered_configs
        
    except Exception as e:
        logger.error(f"Error processing server configs: {e}")
        return []

def is_config_for_profile_inbounds(config, server_inbounds):
    """
    بررسی اینکه آیا یک کانفیگ مربوط به اینباندهای پروفایل است
    """
    try:
        # اگر هیچ اینباندی برای پروفایل تعریف نشده، تمام کانفیگ‌ها را قبول می‌کنیم
        if not server_inbounds:
            return True
        
        # استخراج remark از کانفیگ (اگر موجود باشد)
        config_remark = extract_config_remark(config)
        
        # اگر نتوانستیم remark استخراج کنیم، تمام کانفیگ‌ها را قبول می‌کنیم
        if not config_remark:
            return True
        
        # بررسی اینکه آیا remark با یکی از اینباندهای پروفایل مطابقت دارد
        for inbound_info in server_inbounds:
            inbound_remark = inbound_info.get('remark', '')
            if inbound_remark and config_remark.lower() in inbound_remark.lower():
                return True
            
            # بررسی بر اساس inbound_id نیز
            inbound_id = inbound_info.get('inbound_id')
            if inbound_id and str(inbound_id) in config:
                return True
        
        # اگر هیچ تطابقی پیدا نشد، کانفیگ را رد می‌کنیم
        return False
        
    except Exception as e:
        logger.error(f"Error checking config for profile inbounds: {e}")
        return True  # در صورت خطا، کانفیگ را قبول می‌کنیم

def extract_config_remark(config):
    """
    استخراج remark از کانفیگ
    """
    try:
        # برای VMess
        if 'vmess://' in config:
            import base64
            try:
                # حذف vmess:// و decode کردن
                encoded_part = config.replace('vmess://', '')
                decoded = base64.b64decode(encoded_part + '==').decode('utf-8')
                # استخراج remark از JSON
                import json
                vmess_data = json.loads(decoded)
                return vmess_data.get('ps', '')  # ps = remark در VMess
            except:
                pass
        
        # برای VLESS
        elif 'vless://' in config:
            # استخراج remark از URL
            parts = config.split('#')
            if len(parts) > 1:
                return parts[1]  # remark بعد از #
        
        # برای Trojan
        elif 'trojan://' in config:
            # استخراج remark از URL
            parts = config.split('#')
            if len(parts) > 1:
                return parts[1]  # remark بعد از #
        
        return ''
        
    except Exception as e:
        logger.error(f"Error extracting config remark: {e}")
        return ''

# --- Endpoint زرین‌پال ---
@app.route('/zarinpal/verify', methods=['GET'])
def handle_zarinpal_callback():
    authority = request.args.get('Authority')
    status = request.args.get('Status')

    logger.info(f"Callback received from Zarinpal >> Status: {status}, Authority: {authority}")

    if not authority or not status:
        return render_template('payment_status.html', status='error', message="اطلاعات بازگشتی از درگاه ناقص است.", bot_username=BOT_USERNAME)

    payment = db_manager.get_payment_by_authority(authority)
    if not payment:
        return render_template('payment_status.html', status='error', message="تراکنش یافت نشد.", bot_username=BOT_USERNAME)
    
    user_db_info = db_manager.get_user_by_id(payment['user_id'])
    user_telegram_id = user_db_info['telegram_id']

    if payment['is_confirmed']:
        return render_template('payment_status.html', status='success', ref_id=payment.get('ref_id'), bot_username=BOT_USERNAME)

    if status == 'OK':
        order_details = json.loads(payment['order_details_json'])
        gateway = db_manager.get_payment_gateway_by_id(order_details['gateway_details']['id'])
        
        # مبلغ به ریال برای زرین‌پال ارسال می‌شود
        payload = {"merchant_id": gateway['merchant_id'], "amount": int(payment['amount']) * 10, "authority": authority}
        
        try:
            response = requests.post(ZARINPAL_VERIFY_URL, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()

            if result.get("data") and result.get("data", {}).get("code") in [100, 101]:
                ref_id = result.get("data", {}).get("ref_id", "N/A")
                db_manager.confirm_online_payment(payment['id'], str(ref_id))

                # --- منطق اصلی برای تفکیک نوع تراکنش ---
                if order_details.get('purchase_type') == 'wallet_charge':
                    amount = payment['amount']
                    if db_manager.add_to_user_balance(payment['user_id'], amount):
                        bot.send_message(user_telegram_id, f"✅ کیف پول شما با موفقیت به مبلغ {amount:,.0f} تومان شارژ شد.")
                    else:
                        bot.send_message(user_telegram_id, "❌ خطایی در شارژ کیف پول شما رخ داد. لطفاً با پشتیبانی تماس بگیرید.")

                elif order_details.get('purchase_type') == 'profile':
                    finalize_profile_purchase(bot, db_manager, user_telegram_id, order_details)
                
                else: # خرید عادی سرویس
                    user_db_info = db_manager.get_user_by_telegram_id(user_telegram_id)
                    prompt = bot.send_message(user_telegram_id, messages.ASK_FOR_CUSTOM_CONFIG_NAME)
                    # Note: This part needs a mechanism to communicate with the main bot process
                    # to set the user state. A simple file-based or Redis-based queue could work.
                    # For now, we rely on the admin to complete the process if this part fails.
                    logger.info(f"Online payment for normal service by {user_telegram_id} confirmed. User needs to provide a config name.")
                    bot.send_message(user_telegram_id, "✅ پرداخت شما با موفقیت تایید شد. لطفاً برای دریافت سرویس خود، یک نام دلخواه برای کانفیگ در ربات وارد کنید.")
                
                return render_template('payment_status.html', status='success', ref_id=ref_id, bot_username=BOT_USERNAME)
            else:
                error_message = result.get("errors", {}).get("message", "خطای نامشخص")
                bot.send_message(user_telegram_id, f"❌ پرداخت شما توسط درگاه تایید نشد. (خطا: {error_message})")
                return render_template('payment_status.html', status='error', message=error_message, bot_username=BOT_USERNAME)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying with Zarinpal: {e}")
            return render_template('payment_status.html', status='error', message="خطا در ارتباط با سرور درگاه پرداخت.", bot_username=BOT_USERNAME)
    else:
        bot.send_message(user_telegram_id, "شما فرآیند پرداخت را لغو کردید. سفارش شما ناتمام باقی ماند.")
        return render_template('payment_status.html', status='error', message="تراکنش توسط شما لغو شد.", bot_username=BOT_USERNAME)

# --- Endpoint برای بروزرسانی دستی کانفیگ‌ها ---
@app.route('/admin/update_configs/<purchase_id>', methods=['POST'])
def admin_update_configs(purchase_id):
    """
    Endpoint برای بروزرسانی دستی کانفیگ‌ها توسط ادمین
    """
    try:
        # بررسی احراز هویت
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error(f"Unauthorized access attempt to admin_update_configs for purchase {purchase_id}")
            return Response("Unauthorized", status=401)
        
        api_key = auth_header.split(' ')[1]
        expected_api_key = os.getenv('ADMIN_API_KEY')
        if not expected_api_key:
            logger.error("ADMIN_API_KEY not set in environment")
            return Response("Server configuration error", status=500)
        
        if api_key != expected_api_key:
            logger.error(f"Invalid API key for purchase {purchase_id}")
            return Response("Invalid API key", status=401)
        
        # بررسی وجود purchase
        purchase = db_manager.get_purchase_by_id(int(purchase_id))
        if not purchase:
            logger.error(f"Purchase {purchase_id} not found in database")
            return Response("Purchase not found", status=404)
        
        # بررسی وجود sub_id
        if not purchase.get('sub_id'):
            logger.error(f"Purchase {purchase_id} has no sub_id")
            return Response("Purchase has no subscription ID", status=400)
        
        # بررسی وضعیت purchase
        if not purchase.get('is_active', False):
            logger.warning(f"Purchase {purchase_id} is not active, skipping update")
            return Response("Purchase is not active", status=400)
        
        # بروزرسانی کانفیگ‌ها با logging بیشتر
        logger.info(f"Starting config update for purchase {purchase_id} (type: {'profile' if purchase.get('profile_id') else 'normal'})")
        success = update_cached_configs_from_panel(int(purchase_id))
        
        if success:
            logger.info(f"Successfully updated configs for purchase {purchase_id}")
            return Response("Configs updated successfully", status=200)
        else:
            logger.error(f"Failed to update configs for purchase {purchase_id}")
            return Response("Failed to update configs", status=500)
            
    except ValueError as e:
        logger.error(f"Invalid purchase_id format: {purchase_id}, error: {e}")
        return Response("Invalid purchase ID format", status=400)
    except Exception as e:
        logger.error(f"Unexpected error in admin_update_configs for purchase {purchase_id}: {e}")
        return Response("Internal server error", status=500)

# --- Endpoint تست برای بررسی وضعیت ---
@app.route('/admin/test/<purchase_id>', methods=['GET'])
def admin_test_purchase(purchase_id):
    """
    Endpoint تست برای بررسی وضعیت یک purchase
    """
    try:
        purchase = db_manager.get_purchase_by_id(int(purchase_id))
        if not purchase:
            return Response("Purchase not found", status=404)
        
        result = {
            'purchase_id': purchase['id'],
            'user_id': purchase['user_id'],
            'profile_id': purchase.get('profile_id'),
            'server_id': purchase.get('server_id'),
            'sub_id': purchase.get('sub_id'),
            'is_active': purchase['is_active'],
            'has_configs': bool(purchase.get('single_configs_json'))
        }
        
        return Response(json.dumps(result, indent=2), status=200, mimetype='application/json')
        
    except Exception as e:
        logger.error(f"Error in admin_test_purchase: {e}")
        return Response("Internal server error", status=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)