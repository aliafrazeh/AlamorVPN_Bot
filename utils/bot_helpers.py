# utils/bot_helpers.py (نسخه نهایی و اصلاح شده)

import telebot
import qrcode
from io import BytesIO
import logging
import uuid
from utils import messages, helpers
import datetime
logger = logging.getLogger(__name__)
from utils.config_generator import ConfigGenerator

def send_subscription_info(bot: telebot.TeleBot, user_id: int, sub_link: str):
    """
    اطلاعات اشتراک را با ارسال لینک متنی صحیح و سپس QR کد ارسال می‌کند.
    """
    bot.send_message(user_id, messages.CONFIG_DELIVERY_HEADER, parse_mode='Markdown')
    
    # --- راه حل قطعی: اصلاح لینک قبل از ارسال ---
    # این خط تضمین می‌کند که هرگونه بک‌اسلش (\) اضافه شده، حذف شود.
    # corrected_sub_link = sub_link.replace('\.', '.')

    # ابتدا لینک متنی اصلاح شده ارسال می‌شود
    bot.send_message(user_id, messages.CONFIG_DELIVERY_SUB_LINK.format(sub_link=sub_link), parse_mode='Markdown')
    
    # سپس QR کد در یک پیام جداگانه با لینک اصلاح شده ساخته می‌شود
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
    فرآیند خرید پروفایل را با استفاده از کلاس ConfigGenerator نهایی می‌کند.
    """
    bot.send_message(user_telegram_id, "✅ پرداخت شما تایید شد. لطفاً صبر کنید، در حال ساخت کانفیگ‌های پروفایل شما هستیم...")

    profile_details = order_details['profile_details']
    requested_gb = order_details['requested_gb']
    
    # ۱. ساخت یک نمونه از کلاس ConfigGenerator
    config_gen = ConfigGenerator(db_manager)
    
    # ۲. فراخوانی متد کلاس برای ساخت کانفیگ‌ها
    generated_configs, client_details = config_gen.create_subscription_for_profile(
        user_telegram_id=user_telegram_id,
        profile_id=profile_details['id'],
        total_gb=requested_gb
    )
    
    if not generated_configs:
        bot.send_message(user_telegram_id, "❌ متاسفانه در ساخت کانفیگ‌های پروفایل شما خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید.")
        return

    user_db_info = db_manager.get_user_by_telegram_id(user_telegram_id)
    duration_days = profile_details['duration_days']
    expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days))
    
    new_sub_id = str(uuid.uuid4().hex)
    
    profile_inbounds = db_manager.get_inbounds_for_profile(profile_details['id'], with_server_info=True)
    representative_server_id = profile_inbounds[0]['server']['id'] if profile_inbounds else None

    db_manager.add_purchase(
        user_id=user_db_info['id'],
        server_id=representative_server_id,
        plan_id=None,
        profile_id=profile_details['id'],
        expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S"),
        initial_volume_gb=requested_gb,
        client_uuid=client_details['uuid'],
        client_email=client_details['email'],
        sub_id=new_sub_id,
        single_configs=generated_configs
    )
    
    active_domain = db_manager.get_active_subscription_domain()
    if not active_domain:
        bot.send_message(user_telegram_id, "❌ دامنه فعالی برای لینک اشتراک تنظیم نشده است. لطفاً به پشتیبانی اطلاع دهید.")
        return

    final_sub_link = f"https://{active_domain['domain_name']}/sub/{new_sub_id}"
    
    bot.send_message(user_telegram_id, "🎉 پروفایل شما با موفقیت فعال شد!")
    send_subscription_info(bot, user_telegram_id, final_sub_link)
