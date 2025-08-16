# utils/helpers.py (نسخه کامل و اصلاح شده)

import telebot
import logging
import random
import string
import re
# --- ایمپورت‌های جدید در اینجا اضافه شده‌اند ---
from urllib.parse import urlparse, parse_qs
from database.db_manager import DatabaseManager
import utils.messages as messages_module

from config import ADMIN_IDS
from collections import UserDict

logger = logging.getLogger(__name__)
_db_for_messages = DatabaseManager()

class _SafeFormatDict(UserDict):
    def __missing__(self, key):
        # Leave unknown placeholders intact like {unknown}
        return '{' + key + '}'


def get_message(key: str, **kwargs):
    """Fetches a message template by key (DB overrides > defaults) and safely formats it.

    Unknown placeholders remain unchanged instead of breaking formatting.
    If the DB template is invalid, falls back to the default messages.py template.
    """
    db_template = _db_for_messages.get_message_by_key(key)
    default_template = getattr(messages_module, key, f"MSG_NOT_FOUND: {key}")

    template = db_template if db_template is not None else default_template

    try:
        return template.format_map(_SafeFormatDict(kwargs))
    except Exception:
        # Fallback to default template if DB template is malformed
        try:
            return default_template.format_map(_SafeFormatDict(kwargs))
        except Exception:
            # As a last resort, return unformatted template to avoid crashes
            return default_template
# --- تابع جدید در اینجا اضافه شده است ---
def parse_config_link(link: str) -> dict or None:
    """
    یک لینک کانفیگ vless را تجزیه کرده و به صورت یک دیکشنری ساختاریافته برمی‌گرداند.
    """
    try:
        if not link.startswith("vless://"):
            return None

        parsed_url = urlparse(link)
        
        # استخراج پارامترهای اصلی
        params = {
            "protocol": parsed_url.scheme,
            "uuid": parsed_url.username,
            "hostname": parsed_url.hostname,
            "port": parsed_url.port,
            "remark": parsed_url.fragment
        }
        
        # استخراج تمام پارامترهای کوئری
        query_params = parse_qs(parsed_url.query)
        for key, value in query_params.items():
            # parse_qs مقادیر را به صورت لیست برمی‌گرداند، ما اولین مقدار را می‌خواهیم
            params[key] = value[0]
            
        return params
    except Exception as e:
        logger.error(f"Failed to parse config link '{link}': {e}")
        return None


def is_admin(user_id: int) -> bool:
    """بررسی می‌کند که آیا کاربر ادمین است یا خیر."""
    return user_id in ADMIN_IDS


def is_user_member_of_channel(bot: telebot.TeleBot, channel_id: int, user_id: int) -> bool:
    """
    بررسی می‌کند که آیا کاربر در کانال مورد نظر عضو است یا خیر.
    """
    if channel_id is None:
        return True

    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['member', 'creator', 'administrator']
    except Exception as e:
        logger.error(f"Error checking user {user_id} membership in channel {channel_id}: {e}")
        return True


def is_float_or_int(value) -> bool:
    """
    بررسی می‌کند که آیا یک رشته می‌تواند به float یا int تبدیل شود یا خیر.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def escape_markdown_v1(text: str) -> str:
    """
    کاراکترهای خاص Markdown V1 را برای جلوگیری از خطا در پارس کردن، Escape می‌کند.
    """
    escape_chars = r'_*`[]()~>#+-=|{}!.'

    if not isinstance(text, str):
        text = str(text)

    return text.translate(str.maketrans({c: f'\\{c}' for c in escape_chars}))


def generate_random_string(length=10) -> str:
    """
    یک رشته تصادفی از حروف کوچک و اعداد به طول مشخص تولید می‌کند.
    """
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))


def normalize_panel_inbounds(panel_type, raw_inbounds):
    """
    اطلاعات خام اینباندها از پنل‌های مختلف را گرفته و به یک فرمت استاندارد و یکسان تبدیل می‌کند.
    """
    if not raw_inbounds:
        return []

    normalized_list = []
    
    if panel_type in ['x-ui', 'alireza']:
        for inbound in raw_inbounds:
            normalized_list.append({
                'id': inbound.get('id'),
                'remark': inbound.get('remark', ''),
                'port': inbound.get('port'),
                'protocol': inbound.get('protocol'),
                'settings': inbound.get('settings', '{}'),
                'streamSettings': inbound.get('streamSettings', '{}'),
            })

    return normalized_list


def update_env_file(key_to_update, new_value):
    """یک متغیر خاص را در فایل .env آپدیت یا اضافه می‌کند."""
    env_path = '.env'
    try:
        with open(env_path, 'r') as file:
            lines = file.readlines()

        key_found = False
        with open(env_path, 'w') as file:
            for line in lines:
                if line.strip().startswith(key_to_update + '='):
                    file.write(f'{key_to_update}="{new_value}"\n')
                    key_found = True
                else:
                    file.write(line)
            
            if not key_found:
                file.write(f'\n{key_to_update}="{new_value}"\n')
        return True
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False

def format_traffic_size(bytes_value):
    """
    تبدیل حجم از بایت به فرمت خوانا
    """
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while bytes_value >= 1024 and unit_index < len(units) - 1:
        bytes_value /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{bytes_value:.0f} {units[unit_index]}"
    else:
        return f"{bytes_value:.2f} {units[unit_index]}"

def calculate_days_remaining(expire_date):
    """
    محاسبه تعداد روزهای باقی‌مانده - نسخه ساده و مطمئن
    """
    if not expire_date:
        return None
    
    from datetime import datetime
    
    try:
        # تبدیل expire_date به datetime
        if isinstance(expire_date, str):
            expire_date = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
        
        # حذف timezone اگر وجود دارد
        if hasattr(expire_date, 'tzinfo') and expire_date.tzinfo is not None:
            expire_date = expire_date.replace(tzinfo=None)
        elif hasattr(expire_date, 'replace'):
            # اگر replace method دارد، timezone را حذف کنیم
            expire_date = expire_date.replace(tzinfo=None)
        
        # محاسبه تفاوت با datetime.now() بدون timezone
        now = datetime.now()
        days_remaining = (expire_date - now).days
        return days_remaining
        
    except Exception as e:
        # در صورت بروز خطا، None برمی‌گردانیم
        print(f"Error in calculate_days_remaining: {e}")
        return None