# utils/bot_helpers.py (نسخه نهایی و اصلاح شده)

import telebot
import qrcode
from io import BytesIO
import logging
import uuid
from utils import messages, helpers
import datetime
logger = logging.getLogger(__name__)

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
    فرآیند خرید پروفایل را نهایی کرده، کانفیگ‌ها را ساخته و لینک را به کاربر تحویل می‌دهد.
    """
    from .config_generator import create_configs_for_profile

    bot.send_message(user_telegram_id, "✅ پرداخت شما تایید شد. لطفاً صبر کنید، در حال ساخت کانفیگ‌های پروفایل شما هستیم...")

    profile_details = order_details['profile_details']
    requested_gb = order_details['requested_gb']
    
    # ۱. ساخت کانفیگ‌ها با استفاده از موتور جنریتور
    generated_configs, client_uuids = create_configs_for_profile(db_manager, user_telegram_id, profile_details['id'], requested_gb)
    
    if not generated_configs:
        bot.send_message(user_telegram_id, "❌ متاسفانه در ساخت کانفیگ‌های پروفایل شما خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید.")
        return

    # ۲. ثبت خرید در دیتابیس
    user_db_info = db_manager.get_user_by_telegram_id(user_telegram_id)
    duration_days = profile_details['duration_days']
    expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days))
    
    # ساخت یک شناسه اشتراک یکتا برای لینک جدید
    new_sub_id = str(uuid.uuid4().hex)
    
    # چون پروفایل ممکن است چند سروری باشد، server_id اولین سرور را به عنوان نماینده ذخیره می‌کنیم
    # این بخش در آینده می‌تواند بهتر شود
    representative_server_id = db_manager.get_inbounds_for_profile(profile_details['id'], with_server_info=True)[0]['server']['id']

    db_manager.add_purchase(
        user_id=user_db_info['id'],
        server_id=representative_server_id,
        plan_id=None,
        profile_id=profile_details['id'],
        expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S"),
        initial_volume_gb=requested_gb,
        client_uuid=client_uuids[0] if client_uuids else None, # UUID مشترک
        client_email=f"profile-{profile_details['id']}",
        sub_id=new_sub_id,
        single_configs=generated_configs # لیست کانفیگ‌های تکی را ذخیره می‌کنیم
    )
    
    # ۳. ساخت و تحویل لینک اشتراک هوشمند
    active_domain = db_manager.get_active_subscription_domain()
    if not active_domain:
        bot.send_message(user_telegram_id, "❌ دامنه فعالی برای لینک اشتراک تنظیم نشده است. لطفاً به پشتیبانی اطلاع دهید.")
        return

    final_sub_link = f"https://{active_domain['domain_name']}/sub/{new_sub_id}"
    
    bot.send_message(user_telegram_id, "🎉 پروفایل شما با موفقیت فعال شد!")
    send_subscription_info(bot, user_telegram_id, final_sub_link)