# utils/bot_helpers.py (نسخه نهایی و کامل)

import telebot
import qrcode
from io import BytesIO
import logging
import datetime
import uuid
import json
import os
# ایمپورت‌های پروژه
from .config_generator import ConfigGenerator # کلاس را وارد می‌کنیم
from . import messages, helpers

logger = logging.getLogger(__name__)

def send_subscription_info(bot: telebot.TeleBot, user_id: int, sub_link: str):
    """اطلاعات اشتراک را با ارسال لینک و QR کد ارسال می‌کند."""
    bot.send_message(user_id, messages.CONFIG_DELIVERY_HEADER, parse_mode='Markdown')
    bot.send_message(user_id, messages.CONFIG_DELIVERY_SUB_LINK.format(sub_link=sub_link), parse_mode='Markdown')
    try:
        qr_image = qrcode.make(sub_link)
        bio = BytesIO()
        bio.name = 'qrcode.jpeg'
        qr_image.save(bio, 'JPEG')
        bio.seek(0)
        bot.send_photo(user_id, bio, caption=messages.QR_CODE_CAPTION)
    except Exception as e:
        logger.error(f"Failed to generate or send QR code: {e}")

def finalize_profile_purchase(bot, db_manager, user_telegram_id, order_details):
    """
    فرآیند خرید پروفایل را با استفاده از کلاس ConfigGenerator نهایی می‌کند. (نسخه اصلاح شده)
    """
    bot.send_message(user_telegram_id, "✅ پرداخت شما تایید شد. لطفاً صبر کنید، در حال ساخت کانفیگ‌های پروفایل شما هستیم...")
    
    profile_details = order_details['profile_details']
    requested_gb = order_details['requested_gb']
    
    config_gen = ConfigGenerator(db_manager)
    
    # --- اصلاح اصلی اینجاست ---
    # ما هیچ نامی را به صورت دستی نمی‌سازیم و اجازه می‌دهдим ConfigGenerator کار خود را انجام دهد.
    # با ارسال custom_remark=None، منطق برندینگ در خود ConfigGenerator اجرا خواهد شد.
    generated_configs, client_details = config_gen.create_subscription_for_profile(
        user_telegram_id=user_telegram_id,
        profile_id=profile_details['id'],
        total_gb=requested_gb,
        custom_remark=None 
    )
    
    if not client_details:
        bot.send_message(user_telegram_id, "❌ متاسفانه در ساخت کانفیگ‌های پروفایل شما خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید.")
        return

    user_db_info = db_manager.get_user_by_telegram_id(user_telegram_id)
    duration_days = profile_details['duration_days']
    expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)) if duration_days > 0 else None
    
    new_sub_id = str(uuid.uuid4().hex)
    
    # برای ثبت خرید، به ID یکی از سرورهای پروفایل نیاز داریم
    profile_inbounds = db_manager.get_inbounds_for_profile(profile_details['id'], with_server_info=True)
    representative_server_id = profile_inbounds[0]['server']['id'] if profile_inbounds else None

    # ثبت خرید در دیتابیس
    db_manager.add_purchase(
        user_id=user_db_info['id'], 
        server_id=representative_server_id, 
        plan_id=None,
        profile_id=profile_details['id'], 
        expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S") if expire_date else None,
        initial_volume_gb=requested_gb, 
        client_uuids=client_details['uuids'],
        client_email=client_details['email'], 
        sub_id=new_sub_id,
        single_configs_json=json.dumps(generated_configs)
    )
    
    # تحویل سرویس به کاربر
    active_domain_record = db_manager.get_active_subscription_domain()
    active_domain = active_domain_record['domain_name'] if active_domain_record else None
    
    if not active_domain:
        webhook_domain = os.getenv("WEBHOOK_DOMAIN")
        active_domain = webhook_domain

    if not active_domain:
        bot.send_message(user_telegram_id, "❌ دامنه فعالی برای لینک اشتراک تنظیم نشده است. لطفاً به پشتیبانی اطلاع دهید.")
        return

    final_sub_link = f"https://{active_domain}/sub/{new_sub_id}"
    
    bot.send_message(user_telegram_id, "🎉 پروفایل شما با موفقیت فعال شد!")
    send_subscription_info(bot, user_telegram_id, final_sub_link)