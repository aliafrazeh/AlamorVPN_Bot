# handlers/domain_handlers.py (نسخه نهایی، کامل و یکپارچه)

import telebot
from telebot import types
import logging

# ایمپورت‌های پروژه
from utils import messages, helpers
from keyboards import inline_keyboards
from utils.system_helpers import setup_domain_nginx_and_ssl, remove_domain_nginx_files, check_ssl_certificate_exists
from utils.helpers import update_env_file
from utils.system_helpers import run_shell_command

logger = logging.getLogger(__name__)

# این متغیرها در هنگام ثبت هندلرها مقداردهی می‌شوند
_bot = None
_db_manager = None
_admin_states = None

# =============================================================================
# توابع اصلی و کمکی (در سطح اصلی فایل)
# =============================================================================

def _clear_admin_state(admin_id):
    if admin_id in _admin_states:
        del _admin_states[admin_id]

def _show_menu(user_id, text, markup, message=None, parse_mode='Markdown'):
    try:
        if message:
            return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=parse_mode)
        else:
            return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)
    except telebot.apihelper.ApiTelegramException as e:
        if "can't parse entities" in str(e):
            if message: _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=None)
            else: _bot.send_message(user_id, text, reply_markup=markup, parse_mode=None)
        elif 'message is not modified' not in str(e):
             logger.warning(f"Menu error for {user_id}: {e}")
    return message
    
def show_domain_management_menu(admin_id, message=None):
    domains = _db_manager.get_all_subscription_domains()
    domains_with_status = []
    for row in domains:
        domain_dict = dict(row)
        domain_dict['ssl_status'] = check_ssl_certificate_exists(domain_dict['domain_name'])
        domains_with_status.append(domain_dict)
    markup = inline_keyboards.get_domain_management_menu(domains_with_status)
    _show_menu(admin_id, "🌐 در این بخش می‌توانید دامنه‌های ضد فیلتر را برای لینک‌های اشتراک مدیریت کنید.", markup, message)

def start_add_domain_flow(admin_id, message):
    _clear_admin_state(admin_id)
    prompt = _show_menu(admin_id, messages.ADD_DOMAIN_PROMPT, inline_keyboards.get_back_button("admin_domain_management"), message)
    _admin_states[admin_id] = {'state': 'waiting_for_domain_name', 'data': {}, 'prompt_message_id': prompt.message_id}

def execute_delete_domain(admin_id, message, domain_id):
    domain = next((d for d in _db_manager.get_all_subscription_domains() if d['id'] == domain_id), None)
    if not domain:
        show_domain_management_menu(admin_id, message)
        return
    domain_name = domain['domain_name']
    remove_domain_nginx_files(domain_name)
    _db_manager.delete_subscription_domain(domain_id)
    show_domain_management_menu(admin_id, message)

def start_webhook_setup_flow(admin_id, message):
    """فرآیند تنظیم دامنه وبهوک را شروع می‌کند."""
    _clear_admin_state(admin_id)
    prompt = _show_menu(admin_id, "لطفاً نام دامنه جدید را برای وبهوک و پرداخت آنلاین وارد کنید (مثال: pay.yourdomain.com):", inline_keyboards.get_back_button("admin_main_menu"), message)
    _admin_states[admin_id] = {'state': 'waiting_for_webhook_domain', 'prompt_message_id': prompt.message_id}

def _create_and_start_webhook_service():
    """سرویس systemd برای وبهوک را ایجاد و فعال می‌کند."""
    service_content = """
[Unit]
Description=AlamorBot Webhook Server
After=network.target
[Service]
User=root
WorkingDirectory=/var/www/alamorvpn_bot
ExecStart=/var/www/alamorvpn_bot/.venv/bin/python3 /var/www/alamorvpn_bot/webhook_server.py
Restart=always
RestartSec=10s
[Install]
WantedBy=multi-user.target
"""
    try:
        with open("/tmp/alamor_webhook.service", "w") as f: f.write(service_content)
        run_shell_command(['mv', '/tmp/alamor_webhook.service', '/etc/systemd/system/alamor_webhook.service'])
        run_shell_command(['systemctl', 'daemon-reload'])
        run_shell_command(['systemctl', 'enable', 'alamor_webhook.service'])
        success, output = run_shell_command(['systemctl', 'restart', 'alamor_webhook.service'])
        return success, output
    except Exception as e:
        return False, str(e)

# =============================================================================
# تابع ثبت کننده هندلرها
# =============================================================================
def register_domain_handlers(bot, db_manager, admin_states):
    """تمام هندلرهای مربوط به مدیریت دامنه و وبهوک را ثبت می‌کند."""
    global _bot, _db_manager, _admin_states
    _bot = bot
    _db_manager = db_manager
    _admin_states = admin_states

    # --- Stateful Message Handler ---
    @_bot.message_handler(
        content_types=['text'],
        func=lambda msg: helpers.is_admin(msg.from_user.id) and _admin_states.get(msg.from_user.id, {}).get('state') in [
            'waiting_for_domain_name', 'waiting_for_letsencrypt_email',
            'waiting_for_webhook_domain', 'waiting_for_webhook_email'
        ]
    )
    def handle_domain_stateful_messages(message):
        admin_id = message.from_user.id
        state_info = _admin_states.get(admin_id)
        if not state_info: return

        state = state_info.get("state")
        prompt_id = state_info.get("prompt_message_id")
        data = state_info.get("data", {})
        text = message.text.strip()
        
        if state == 'waiting_for_domain_name':
            domain_name = text.lower()
            state_info['state'] = 'waiting_for_letsencrypt_email'
            state_info['data']['domain_name'] = domain_name
            _bot.edit_message_text("برای دریافت گواهی SSL، لطفاً آدرس ایمیل خود را وارد کنید:", admin_id, prompt_id)
        
        elif state == 'waiting_for_letsencrypt_email':
            admin_email = text
            _db_manager.update_setting('letsencrypt_email', admin_email)
            domain_name = data['domain_name']
            _bot.edit_message_text(f"⏳ لطفاً صبر کنید...\nدر حال تنظیم دامنه {domain_name} و دریافت گواهی SSL...", admin_id, prompt_id)
            success, message_text = setup_domain_nginx_and_ssl(domain_name, admin_email)
            if success:
                if _db_manager.add_subscription_domain(domain_name):
                     _bot.send_message(admin_id, f"✅ دامنه {domain_name} اضافه و SSL برای آن فعال گردید.")
                else:
                     _bot.send_message(admin_id, "❌ دامنه در Nginx تنظیم شد، اما در ذخیره در دیتابیس خطایی رخ داد.")
            else:
                _bot.send_message(admin_id, f"❌ عملیات ناموفق بود.\nعلت: {message_text}")
            _clear_admin_state(admin_id)
            show_domain_management_menu(admin_id)
            
        elif state == 'waiting_for_webhook_domain':
            domain_name = text.lower()
            state_info['data'] = {'domain_name': domain_name}
            state_info['state'] = 'waiting_for_webhook_email'
            _bot.edit_message_text("برای دریافت گواهی SSL، لطفاً ایمیل خود را وارد کنید:", admin_id, prompt_id)

        elif state == 'waiting_for_webhook_email':
            admin_email = text.lower()
            domain_name = data['domain_name']
            _bot.edit_message_text(f"⏳ لطفاً صبر کنید...\nدر حال تنظیم دامنه وبهوک {domain_name}...", admin_id, prompt_id)
            ssl_success, ssl_message = setup_domain_nginx_and_ssl(domain_name, admin_email)
            if not ssl_success:
                _bot.send_message(admin_id, f"❌ عملیات ناموفق بود.\nعلت: {ssl_message}")
            elif not update_env_file('WEBHOOK_DOMAIN', domain_name):
                _bot.send_message(admin_id, "❌ دامنه تنظیم شد، اما در آپدیت فایل .env خطایی رخ داد.")
            else:
                service_success, service_output = _create_and_start_webhook_service()
                if not service_success:
                    _bot.send_message(admin_id, f"❌ دامنه و .env تنظیم شدند، اما در راه‌اندازی سرویس وبهوک خطایی رخ داد:\n`{service_output}`")
                else:
                    _bot.send_message(admin_id, "✅ عملیات با موفقیت کامل شد! دامنه تنظیم و سرویس وبهوک فعال گردید.")
            _clear_admin_state(admin_id)
            from handlers.admin_handlers import _show_admin_main_menu
            _show_admin_main_menu(admin_id)

    # --- Callback Handler ---
    @_bot.callback_query_handler(
        func=lambda call: helpers.is_admin(call.from_user.id) and call.data.startswith('admin_') and 'domain' in call.data
    )
    def handle_domain_callbacks(call):
        admin_id, message, data = call.from_user.id, call.message, call.data

        if data == "admin_domain_management":
            _clear_admin_state(admin_id)
            show_domain_management_menu(admin_id, message)
        elif data == "admin_add_domain":
            _bot.answer_callback_query(call.id)
            start_add_domain_flow(admin_id, message)
        elif data.startswith("admin_activate_domain_"):
            _bot.answer_callback_query(call.id)
            domain_id = int(data.split('_')[-1])
            _db_manager.set_active_subscription_domain(domain_id)
            show_domain_management_menu(admin_id, message)
        elif data.startswith("admin_delete_domain_"):
            domain_id = int(data.split('_')[-1])
            domain = next((d for d in _db_manager.get_all_subscription_domains() if d['id'] == domain_id), None)
            if domain:
                confirm_markup = inline_keyboards.get_confirmation_menu(f"confirm_delete_domain_{domain_id}", "admin_domain_management")
                _show_menu(admin_id, f"⚠️ آیا از حذف دامنه {domain['domain_name']} مطمئن هستید؟", confirm_markup, message)
        elif data.startswith("confirm_delete_domain_"):
            _bot.answer_callback_query(call.id, "⏳ در حال حذف دامنه...")
            domain_id = int(data.split('_')[-1])
            execute_delete_domain(admin_id, message, domain_id)
            
            
            
            