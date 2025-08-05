# webhook_server.py

from flask import Flask, request, render_template, Response
import requests
import json
import logging
import os
import sys
import datetime
import base64

# افزودن مسیر پروژه به sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# وارد کردن ماژول‌های پروژه
from config import BOT_TOKEN, BOT_USERNAME_ALAMOR # <-- اصلاح شد
from database.db_manager import DatabaseManager
from utils.bot_helpers import send_subscription_info
from utils.config_generator import ConfigGenerator
from api_client.xui_api_client import XuiAPIClient
import telebot

# تنظیمات اولیه
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
db_manager = DatabaseManager()
bot = telebot.TeleBot(BOT_TOKEN)
config_gen = ConfigGenerator(XuiAPIClient, db_manager)

# آدرس API واقعی زرین‌پال
ZARINPAL_VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
BOT_USERNAME = BOT_USERNAME_ALAMOR # <-- اصلاح شد

@app.route('/', methods=['GET'])
def index():
    return "AlamorVPN Bot Webhook Server is running."
def build_config_link(synced_config, client_uuid, client_remark, active_domain):
    """
    با استفاده از اطلاعات خام همگام‌سازی شده، لینک کانفیگ نهایی را می‌سازد.
    """
    try:
        # جایگزین کردن آدرس سرور اصلی با دامنه ضد فیلتر
        address = active_domain
        port = synced_config['port']
        remark = f"{client_remark} - {synced_config['remark']}"
        
        # فرض ما بر VLESS/TCP است (رایج‌ترین حالت)
        if synced_config['protocol'] == 'vless':
            stream_settings = json.loads(synced_config['stream_settings'])
            link = (
                f"vless://{client_uuid}@{address}:{port}"
                f"?type={stream_settings.get('network', 'tcp')}"
                f"&security={stream_settings.get('security', 'none')}"
                f"#{remark}"
            )
            return link
        # در آینده می‌توان پروتکل‌های دیگر را نیز اینجا اضافه کرد
        
    except Exception as e:
        logger.error(f"Error building config link for inbound {synced_config['inbound_id']}: {e}")
        return None
@app.route('/zarinpal/verify', methods=['GET'])
def handle_zarinpal_callback():
    authority = request.args.get('Authority')
    status = request.args.get('Status')

    logger.info(f"Callback received from Zarinpal >> Status: {status}, Authority: {authority}")

    if not authority or not status:
        return render_template('payment_status.html', status='error', message="اطلاعات بازگشتی از درگاه ناقص است.", bot_username=BOT_USERNAME)

    payment = db_manager.get_payment_by_authority(authority)
    if not payment:
        logger.warning(f"Payment not found for Authority: {authority}")
        return render_template('payment_status.html', status='error', message="تراکنش یافت نشد.", bot_username=BOT_USERNAME)
    
    user_db_info = db_manager.get_user_by_id(payment['user_id'])
    user_telegram_id = user_db_info['telegram_id']

    if payment['is_confirmed']:
        logger.warning(f"Payment ID {payment['id']} has already been confirmed.")
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
                logger.info(f"Payment {payment['id']} verified successfully. Ref ID: {ref_id}")
                
                if order_details['plan_type'] == 'fixed_monthly':
                    plan = order_details['plan_details']
                    total_gb, duration_days = plan['volume_gb'], plan['duration_days']
                else:
                    gb_plan = order_details['gb_plan_details']
                    total_gb, duration_days = order_details['requested_gb'], gb_plan.get('duration_days', 0)
                
                client_details, sub_link, single_configs = config_gen.create_client_and_configs(user_telegram_id, order_details['server_id'], total_gb, duration_days)
                
                if sub_link:
                    expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)) if duration_days and duration_days > 0 else None
                    plan_id = order_details.get('plan_details', {}).get('id') or order_details.get('gb_plan_details', {}).get('id')
                    
                    db_manager.add_purchase(
                        user_id=payment['user_id'], server_id=order_details['server_id'], plan_id=plan_id,
                        expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S") if expire_date else None,
                        initial_volume_gb=total_gb, client_uuid=client_details['uuid'],
                        client_email=client_details['email'], sub_id=client_details['subscription_id'],
                        single_configs=single_configs
                    )
                    
                    db_manager.confirm_online_payment(payment['id'], str(ref_id))
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
# --- Endpoint جدید برای سرور اشتراک ---
@app.route('/sub/<sub_id>', methods=['GET'])
def serve_subscription(sub_id):
    logger.info(f"Subscription request received for sub_id: {sub_id}")
    
    # ۱. پیدا کردن خرید مربوط به این sub_id
    purchase = db_manager.get_purchase_by_sub_id(sub_id)
    if not purchase or not purchase['is_active']:
        return Response("Subscription not found or is inactive.", status=404)
        
    # ۲. پیدا کردن دامنه فعال
    active_domain_record = db_manager.get_active_subscription_domain()
    if not active_domain_record:
        return Response("No active subscription domain is configured.", status=500)
    active_domain = active_domain_record['domain_name']

    # ۳. دریافت کانفیگ‌های مربوط به این خرید
    # فعلا فقط پروفایل‌ها این نوع لینک را دارند
    # TODO: این منطق باید برای خرید عادی نیز در آینده توسعه یابد
    if purchase.get('profile_id'):
        synced_configs = db_manager.get_synced_configs_for_profile(purchase['profile_id'])
    else:
        # منطق برای خرید عادی در اینجا اضافه خواهد شد
        return Response("Subscription type not supported yet.", status=500)

    if not synced_configs:
        return Response("No configurations found for this subscription.", status=404)
        
    # ۴. ساخت لینک‌های کانفیگ نهایی
    all_config_links = []
    client_uuid = purchase['client_uuid'] # UUID مشترک برای همه کانفیگ‌ها
    client_remark = f"AlamorVPN-{purchase['id']}" # نام دلخواه
    
    for config_data in synced_configs:
        link = build_config_link(config_data, client_uuid, client_remark, active_domain)
        if link:
            all_config_links.append(link)
            
    # ۵. ترکیب و کد کردن لینک‌ها
    final_subscription_content = "\n".join(all_config_links)
    encoded_content = base64.b64encode(final_subscription_content.encode('utf-8')).decode('utf-8')
    
    return Response(encoded_content, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)