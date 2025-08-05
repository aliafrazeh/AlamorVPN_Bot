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
# --- Endpoint جدید برای سرور اشتراک ---
@app.route('/sub/<sub_id>', methods=['GET'])
def serve_subscription(sub_id):
    logger.info(f"Subscription request received for sub_id: {sub_id}")
    
    purchase = db_manager.get_purchase_by_sub_id(sub_id)
    if not purchase or not purchase['is_active']:
        return Response("Subscription not found or is inactive.", status=404)
        
    synced_configs = []
    if purchase.get('profile_id'):
        synced_configs = db_manager.get_synced_configs_for_profile(purchase['profile_id'])
    else:
        # برای خرید عادی، از کانفیگ‌های تکی ذخیره شده استفاده می‌کنیم
        single_configs_str = purchase.get('single_configs_json')
        if single_configs_str:
            try:
                # چون single_configs_str ممکن است خودش یک رشته JSON از لیست باشد
                # ابتدا آن را به لیست پایتون تبدیل می‌کنیم
                config_list = json.loads(single_configs_str)
                final_subscription_content = "\n".join(config_list)
                encoded_content = base64.b64encode(final_subscription_content.encode('utf-8')).decode('utf-8')
                return Response(encoded_content, mimetype='text/plain')
            except (json.JSONDecodeError, TypeError):
                 return Response("Error processing normal subscription configs.", status=500)
        
    if not synced_configs:
        return Response("No configurations found for this subscription.", status=404)
        
    all_config_links = []
    client_uuid_list_str = purchase.get('client_uuid')
    try:
        # UUID ها به صورت رشته JSON ذخیره شده‌اند
        client_uuids = json.loads(client_uuid_list_str)
    except (json.JSONDecodeError, TypeError):
        client_uuids = []

    client_remark = f"AlamorVPN-{purchase['id']}"
    
    for config_data in synced_configs:
        # برای پروفایل‌ها، از اولین UUID در لیست استفاده می‌کنیم (چون همه یکی هستند)
        # در آینده می‌توان این منطق را برای UUID های متفاوت نیز توسعه داد
        current_uuid = client_uuids[0] if client_uuids else ''
        
        # --- اصلاح اصلی اینجاست: آرگومان چهارم حذف شد ---
        link = build_config_link(config_data, current_uuid, client_remark)
        if link:
            all_config_links.append(link)
            
    final_subscription_content = "\n".join(all_config_links)
    encoded_content = base64.b64encode(final_subscription_content.encode('utf-8')).decode('utf-8')
    
    return Response(encoded_content, mimetype='text/plain')
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
        
        payload = {"merchant_id": gateway['merchant_id'], "amount": int(payment['amount']) * 10, "authority": authority}
        
        try:
            response = requests.post(ZARINPAL_VERIFY_URL, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()

            if result.get("data") and result.get("data", {}).get("code") in [100, 101]:
                ref_id = result.get("data", {}).get("ref_id", "N/A")
                db_manager.confirm_online_payment(payment['id'], str(ref_id))

                if order_details.get('purchase_type') == 'profile':
                    finalize_profile_purchase(bot, db_manager, user_telegram_id, order_details)
                else:
                    # منطق خرید عادی آنلاین
                    if order_details['plan_type'] == 'fixed_monthly':
                        plan = order_details['plan_details']
                        total_gb, duration_days = plan['volume_gb'], plan['duration_days']
                    else:
                        gb_plan = order_details['gb_plan_details']
                        total_gb, duration_days = order_details['requested_gb'], gb_plan.get('duration_days', 0)
                    
                    client_details, sub_link = config_gen_normal.create_client_and_configs(user_telegram_id, order_details['server_id'], total_gb, duration_days)
                    
                    if sub_link:
                        expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)) if duration_days and duration_days > 0 else None
                        plan_id = order_details.get('plan_details', {}).get('id') or order_details.get('gb_plan_details', {}).get('id')
                        
                        db_manager.add_purchase(
                            user_id=payment['user_id'], server_id=order_details['server_id'], plan_id=plan_id,
                            expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S") if expire_date else None,
                            initial_volume_gb=total_gb, client_uuid=client_details['uuid'],
                            client_email=client_details['email'], sub_id=client_details['subscription_id'],
                            single_configs=None, # برای خرید عادی فعلا لینک‌های تکی نداریم
                            profile_id=None
                        )
                        
                        bot.send_message(user_telegram_id, "✅ پرداخت شما با موفقیت تایید و سرویس شما فعال گردید.")
                        send_subscription_info(bot, user_telegram_id, sub_link)
                    else:
                        bot.send_message(user_telegram_id, "❌ در فعال‌سازی سرویس شما خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید.")
                
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)