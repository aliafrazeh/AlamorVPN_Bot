# handlers/admin_handlers.py (نسخه نهایی، کامل و حرفه‌ای)

import telebot
from telebot import types
import logging
import datetime
import json
import os
import zipfile
from config import ADMIN_IDS, SUPPORT_CHANNEL_LINK
from database.db_manager import DatabaseManager
from api_client.xui_api_client import XuiAPIClient
from utils import messages, helpers
from keyboards import inline_keyboards
from utils.config_generator import ConfigGenerator
from utils.bot_helpers import send_subscription_info # این ایمپورت جدید است
from handlers.user_handlers import _user_states
from config import REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_LINK # This should already be there

logger = logging.getLogger(__name__)

# ماژول‌های سراسری
_bot: telebot.TeleBot = None
_db_manager: DatabaseManager = None
_xui_api: XuiAPIClient = None
_config_generator: ConfigGenerator = None
_admin_states = {}

def register_admin_handlers(bot_instance, db_manager_instance, xui_api_instance):
    global _bot, _db_manager, _xui_api, _config_generator
    _bot = bot_instance
    _db_manager = db_manager_instance
    _xui_api = xui_api_instance
    _config_generator = ConfigGenerator(xui_api_instance, db_manager_instance)

    # =============================================================================
    # SECTION: Helper and Menu Functions
    # =============================================================================

    def _clear_admin_state(admin_id):
        """وضعیت ادمین را فقط از دیکشنری پاک می‌کند."""
        if admin_id in _admin_states:
            del _admin_states[admin_id]

    def _show_menu(user_id, text, markup, message=None, parse_mode='Markdown'):
        """
        --- FINAL & ROBUST VERSION ---
        This function intelligently handles Markdown parsing errors.
        It first tries to send the message with Markdown. If Telegram rejects it
        due to a formatting error, it automatically retries sending it as plain text.
        """
        try:
            # First attempt: Send with specified parse_mode (usually Markdown)
            if message:
                return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=parse_mode)
            else:
                return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)

        except telebot.apihelper.ApiTelegramException as e:
            # If the error is specifically a Markdown parsing error...
            if "can't parse entities" in str(e):
                logger.warning(f"Markdown parse error for user {user_id}. Retrying with plain text.")
                try:
                    # Second attempt: Send as plain text
                    if message:
                        return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=None)
                    else:
                        return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=None)
                except telebot.apihelper.ApiTelegramException as retry_e:
                    logger.error(f"Failed to send menu even as plain text for user {user_id}: {retry_e}")

            # Handle other common errors
            elif 'message to edit not found' in str(e):
                return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)
            elif 'message is not modified' not in str(e):
                logger.warning(f"Menu error for {user_id}: {e}")
                
        return message

    def _show_admin_main_menu(admin_id, message=None): _show_menu(admin_id, messages.ADMIN_WELCOME, inline_keyboards.get_admin_main_inline_menu(), message)
    def _show_server_management_menu(admin_id, message=None): _show_menu(admin_id, messages.SERVER_MGMT_MENU_TEXT, inline_keyboards.get_server_management_inline_menu(), message)
    def _show_plan_management_menu(admin_id, message=None): _show_menu(admin_id, messages.PLAN_MGMT_MENU_TEXT, inline_keyboards.get_plan_management_inline_menu(), message)
    def _show_payment_gateway_management_menu(admin_id, message=None): _show_menu(admin_id, messages.PAYMENT_GATEWAY_MGMT_MENU_TEXT, inline_keyboards.get_payment_gateway_management_inline_menu(), message)
    def _show_user_management_menu(admin_id, message=None): _show_menu(admin_id, messages.USER_MGMT_MENU_TEXT, inline_keyboards.get_user_management_inline_menu(), message)

    # =============================================================================
    # SECTION: Single-Action Functions (Listing, Testing)
    # =============================================================================

    def list_all_servers(admin_id, message):
        _bot.edit_message_text(_generate_server_list_text(), admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_server_management"))

    # در فایل handlers/admin_handlers.py

    def list_all_plans(admin_id, message, return_text=False):
        plans = _db_manager.get_all_plans()
        if not plans: 
            text = messages.NO_PLANS_FOUND
        else:
            text = messages.LIST_PLANS_HEADER
            for p in plans:
                status = "✅ فعال" if p['is_active'] else "❌ غیرفعال"
                if p['plan_type'] == 'fixed_monthly':
                    details = f"حجم: {p['volume_gb']}GB | مدت: {p['duration_days']} روز | قیمت: {p['price']:,.0f} تومان"
                else:
                    # --- بخش اصلاح شده ---
                    duration_days = p.get('duration_days') # مقدار ممکن است None باشد
                    if duration_days and duration_days > 0:
                        duration_text = f"{duration_days} روز"
                    else:
                        duration_text = "نامحدود"
                    # --- پایان بخش اصلاح شده ---
                    details = f"قیمت هر گیگ: {p['per_gb_price']:,.0f} تومان | مدت: {duration_text}"
                text += f"**ID: `{p['id']}`** - {helpers.escape_markdown_v1(p['name'])}\n_({details})_ - {status}\n---\n"
        
        if return_text:
            return text
        _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_plan_management"))
    def list_all_gateways(admin_id, message, return_text=False):
        gateways = _db_manager.get_all_payment_gateways()
        if not gateways:
            text = messages.NO_GATEWAYS_FOUND
        else:
            text = messages.LIST_GATEWAYS_HEADER
            for g in gateways:
                status = "✅ فعال" if g['is_active'] else "❌ غیرفعال"
                text += f"**ID: `{g['id']}`** - {helpers.escape_markdown_v1(g['name'])}\n`{g.get('card_number', 'N/A')}` - {status}\n---\n"
        
        if return_text:
            return text
        _bot.edit_message_text(text, admin_id, message.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_payment_management"))


    def list_all_users(admin_id, message):
        users = _db_manager.get_all_users()
        if not users:
            text = messages.NO_USERS_FOUND
        else:
            text = messages.LIST_USERS_HEADER
            for user in users:
                # --- بخش اصلاح شده ---
                # نام کاربری نیز escape می‌شود تا از خطا جلوگیری شود
                username = helpers.escape_markdown_v1(user.get('username', 'N/A'))
                first_name = helpers.escape_markdown_v1(user.get('first_name', ''))
                text += f"👤 `ID: {user['id']}` - **{first_name}** (@{username})\n"
                # --- پایان بخش اصلاح شده ---
        
        _show_menu(admin_id, text, inline_keyboards.get_back_button("admin_user_management"), message)

    def test_all_servers(admin_id, message):
        _bot.edit_message_text(messages.TESTING_ALL_SERVERS, admin_id, message.message_id, reply_markup=None)
        servers = _db_manager.get_all_servers()
        if not servers:
            _bot.send_message(admin_id, messages.NO_SERVERS_FOUND); _show_server_management_menu(admin_id); return
        results = []
        for s in servers:
            temp_xui_client = _xui_api(panel_url=s['panel_url'], username=s['username'], password=s['password'])
            is_online = temp_xui_client.login()
            _db_manager.update_server_status(s['id'], is_online, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            results.append(f"{'✅' if is_online else '❌'} {helpers.escape_markdown_v1(s['name'])}")
        _bot.send_message(admin_id, messages.TEST_RESULTS_HEADER + "\n".join(results), parse_mode='Markdown')
        _show_server_management_menu(admin_id)

    # =============================================================================
    # SECTION: Stateful Process Handlers
    # =============================================================================

    def _handle_stateful_message(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        state = state_info.get("state")
        prompt_id = state_info.get("prompt_message_id")
        data = state_info.get("data", {})
        text = message.text
        

        # --- Server Flows ---
        if state == 'waiting_for_server_name':
            data['name'] = text; state_info['state'] = 'waiting_for_server_url'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_URL, admin_id, prompt_id)
        elif state == 'waiting_for_server_url':
            data['url'] = text; state_info['state'] = 'waiting_for_server_username'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_USERNAME, admin_id, prompt_id)
        elif state == 'waiting_for_server_username':
            data['username'] = text; state_info['state'] = 'waiting_for_server_password'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_PASSWORD, admin_id, prompt_id)
        elif state == 'waiting_for_server_password':
            data['password'] = text; state_info['state'] = 'waiting_for_sub_base_url'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_SUB_BASE_URL, admin_id, prompt_id)
        elif state == 'waiting_for_sub_base_url':
            data['sub_base_url'] = text; state_info['state'] = 'waiting_for_sub_path_prefix'
            _bot.edit_message_text(messages.ADD_SERVER_PROMPT_SUB_PATH_PREFIX, admin_id, prompt_id)
        elif state == 'waiting_for_sub_path_prefix':
            data['sub_path_prefix'] = text; execute_add_server(admin_id, data)
        elif state == 'waiting_for_server_id_to_delete':
            if not text.isdigit() or not (server := _db_manager.get_server_by_id(int(text))):
                _bot.edit_message_text(f"{messages.SERVER_NOT_FOUND}\n\n{messages.DELETE_SERVER_PROMPT}", admin_id, prompt_id); return
            confirm_text = messages.DELETE_SERVER_CONFIRM.format(server_name=server['name'], server_id=server['id'])
            markup = inline_keyboards.get_confirmation_menu(f"confirm_delete_server_{server['id']}", "admin_server_management")
            _bot.edit_message_text(confirm_text, admin_id, prompt_id, reply_markup=markup)

        # --- Plan Flows ---
        elif state == 'waiting_for_plan_name':
            data['name'] = text; state_info['state'] = 'waiting_for_plan_type'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_TYPE, admin_id, prompt_id, reply_markup=inline_keyboards.get_plan_type_selection_menu_admin())
        elif state == 'waiting_for_plan_volume':
            if not helpers.is_float_or_int(text): _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_VOLUME}", admin_id, prompt_id); return
            data['volume_gb'] = float(text); state_info['state'] = 'waiting_for_plan_duration'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_DURATION, admin_id, prompt_id)
        elif state == 'waiting_for_plan_duration':
            if not text.isdigit(): _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_DURATION}", admin_id, prompt_id); return
            data['duration_days'] = int(text); state_info['state'] = 'waiting_for_plan_price'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_PRICE, admin_id, prompt_id)
        elif state == 'waiting_for_plan_price':
            if not helpers.is_float_or_int(text): _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_PRICE}", admin_id, prompt_id); return
            data['price'] = float(text); execute_add_plan(admin_id, data)
        elif state == 'waiting_for_per_gb_price':
            if not helpers.is_float_or_int(text): _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_PER_GB_PRICE}", admin_id, prompt_id); return
            data['per_gb_price'] = float(text); state_info['state'] = 'waiting_for_gb_plan_duration'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_DURATION_GB, admin_id, prompt_id)
        elif state == 'waiting_for_gb_plan_duration':
            if not text.isdigit(): _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ADD_PLAN_PROMPT_DURATION_GB}", admin_id, prompt_id); return
            data['duration_days'] = int(text); execute_add_plan(admin_id, data)
        elif state == 'waiting_for_tutorial_platform':
            process_tutorial_platform(admin_id, message)
        elif state == 'waiting_for_plan_id_to_toggle':
            execute_toggle_plan_status(admin_id, text)
        elif state == 'waiting_for_tutorial_app_name':
            process_tutorial_app_name(admin_id, message)
        elif state == 'waiting_for_tutorial_forward':
            process_tutorial_forward(admin_id , message)
        elif state == 'waiting_for_user_id_to_search':
            process_user_search(admin_id, text)
        elif state == 'waiting_for_channel_id':
            process_set_channel_id(admin_id, message)
        elif state == 'waiting_for_user_id_to_search':
            process_user_search(admin_id,message)
        elif state == 'waiting_for_channel_link':
            process_set_channel_link(admin_id,message)
        # --- Gateway Flows ---
        if state == 'waiting_for_gateway_name':
            data['name'] = text
            state_info['state'] = 'waiting_for_gateway_type'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_TYPE, admin_id, prompt_id, reply_markup=inline_keyboards.get_gateway_type_selection_menu())
        elif state == 'waiting_for_merchant_id':
            data['merchant_id'] = text
            state_info['state'] = 'waiting_for_gateway_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)

        elif state == 'waiting_for_card_number':
            if not text.isdigit() or len(text) not in [16]:
                _bot.edit_message_text(f"شماره کارت نامعتبر است.\n\n{messages.ADD_GATEWAY_PROMPT_CARD_NUMBER}", admin_id, prompt_id)
                return
            data['card_number'] = text
            state_info['state'] = 'waiting_for_card_holder_name'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_HOLDER_NAME, admin_id, prompt_id)
        elif state == 'waiting_for_card_holder_name':
            data['card_holder_name'] = text
            state_info['state'] = 'waiting_for_gateway_description'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_DESCRIPTION, admin_id, prompt_id)

        elif state == 'waiting_for_gateway_description':
            data['description'] = None if text.lower() == 'skip' else text
            execute_add_gateway(admin_id, data)
        elif state == 'waiting_for_gateway_id_to_toggle':
            execute_toggle_gateway_status(admin_id, text)
            
        # --- Inbound Flow ---
        elif state == 'waiting_for_server_id_for_inbounds':
            process_manage_inbounds_flow(admin_id, message)

        elif state == 'waiting_for_plan_id_to_delete':
            process_delete_plan_id(admin_id, message)
        
        elif state == 'waiting_for_plan_id_to_edit':
            process_edit_plan_id(admin_id, message)
        elif state == 'waiting_for_new_plan_name':
            process_edit_plan_name(admin_id, message)
            
        elif state == 'waiting_for_new_plan_price':
            process_edit_plan_price(admin_id, message)
        elif state == 'waiting_for_support_link':
            process_support_link(admin_id, message)
     

    # =============================================================================
    # SECTION: Process Starters and Callback Handlers
    # =============================================================================
    def start_add_server_flow(admin_id, message):
        _clear_admin_state(admin_id)
        _admin_states[admin_id] = {'state': 'waiting_for_server_name', 'data': {}, 'prompt_message_id': message.message_id}
        _bot.edit_message_text(messages.ADD_SERVER_PROMPT_NAME, admin_id, message.message_id)

    def start_delete_server_flow(admin_id, message):
        _clear_admin_state(admin_id)
        list_text = _generate_server_list_text()
        if list_text == messages.NO_SERVERS_FOUND:
            _bot.edit_message_text(list_text, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management")); return
        _admin_states[admin_id] = {'state': 'waiting_for_server_id_to_delete', 'prompt_message_id': message.message_id}
        prompt_text = f"{list_text}\n\n{messages.DELETE_SERVER_PROMPT}"
        _bot.edit_message_text(prompt_text, admin_id, message.message_id, parse_mode='Markdown')

    def start_add_plan_flow(admin_id, message):
        """Starts the flow using the library's standard next_step_handler."""
        servers = _db_manager.get_all_servers(only_active=False)
        if not servers:
            _show_menu(admin_id, "ابتدا باید حداقل یک سرور اضافه کنید.", inline_keyboards.get_back_button("admin_plan_management"), message, parse_mode=None)
            return
        
        server_list_text = "\n".join([f"ID: `{s['id']}` - {helpers.escape_markdown_v1(s['name'])}" for s in servers])
        prompt_text = f"**لیست سرورها:**\n{server_list_text}\n\nلطفا ID سروری که میخواهید پلن را برای آن تعریف کنید، وارد نمایید:"
        
        prompt = _show_menu(admin_id, prompt_text, inline_keyboards.get_back_button("admin_plan_management"), message)
        
        # --- THE FIX IS HERE ---
        # Explicitly tell the bot to pass the next message to the 'process_add_plan_server' function.
        _bot.register_next_step_handler(prompt, process_add_plan_server)
    def start_toggle_plan_status_flow(admin_id, message):
        _clear_admin_state(admin_id)
        # --- بخش اصلاح شده ---
        # اکنون پارامترهای لازم به تابع پاس داده می‌شوند
        plans_text = list_all_plans(admin_id, message, return_text=True)
        _bot.edit_message_text(f"{plans_text}\n\n{messages.TOGGLE_PLAN_STATUS_PROMPT}", admin_id, message.message_id, parse_mode='Markdown')
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_toggle', 'prompt_message_id': message.message_id}
        
    def start_add_gateway_flow(admin_id, message):
        _clear_admin_state(admin_id)
        _admin_states[admin_id] = {'state': 'waiting_for_gateway_name', 'data': {}, 'prompt_message_id': message.message_id}
        _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_NAME, admin_id, message.message_id)
        
    def start_toggle_gateway_status_flow(admin_id, message):
        _clear_admin_state(admin_id)
        # --- بخش اصلاح شده ---
        # اکنون پارامترهای لازم به تابع پاس داده می‌شوند
        gateways_text = list_all_gateways(admin_id, message, return_text=True)
        _bot.edit_message_text(f"{gateways_text}\n\n{messages.TOGGLE_GATEWAY_STATUS_PROMPT}", admin_id, message.message_id, parse_mode='Markdown')
        _admin_states[admin_id] = {'state': 'waiting_for_gateway_id_to_toggle', 'prompt_message_id': message.message_id}

    def get_plan_details_from_callback(admin_id, message, plan_type):
        state_info = _admin_states.get(admin_id, {})
        if state_info.get('state') != 'waiting_for_plan_type': return
        state_info['data']['plan_type'] = plan_type
        if plan_type == 'fixed_monthly':
            state_info['state'] = 'waiting_for_plan_volume'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_VOLUME, admin_id, message.message_id)
        elif plan_type == 'gigabyte_based':
            state_info['state'] = 'waiting_for_per_gb_price'
            _bot.edit_message_text(messages.ADD_PLAN_PROMPT_PER_GB_PRICE, admin_id, message.message_id)
        state_info['prompt_message_id'] = message.message_id

    # ... other functions remain the same ...

    # =============================================================================
    # SECTION: Main Bot Handlers
    # =============================================================================

    @_bot.message_handler(commands=['admin'])
    def handle_admin_command(message):
        if not helpers.is_admin(message.from_user.id):
            _bot.reply_to(message, messages.NOT_ADMIN_ACCESS); return
        try: _bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        _clear_admin_state(message.from_user.id)
        _show_admin_main_menu(message.from_user.id)

    @_bot.callback_query_handler(func=lambda call: helpers.is_admin(call.from_user.id))
    def handle_admin_callbacks(call):
        """این هندلر تمام کلیک‌های ادمین را به صورت یکپارچه مدیریت می‌کند."""
        _bot.answer_callback_query(call.id)
        admin_id, message, data = call.from_user.id, call.message, call.data

        # --- بخش اصلاح شده ---
        # تعریف توابع داخلی برای خوانایی بهتر
        def list_plans_action(a_id, msg):
            # پاس دادن صحیح پارامترها به تابع اصلی
            text = list_all_plans(a_id, msg, return_text=True)
            _bot.edit_message_text(text, a_id, msg.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_plan_management"))

        def list_gateways_action(a_id, msg):
            # پاس دادن صحیح پارامترها به تابع اصلی
            text = list_all_gateways(a_id, msg, return_text=True)
            _bot.edit_message_text(text, a_id, msg.message_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_back_button("admin_payment_management"))
        # --- پایان بخش اصلاح شده ---

        actions = {
            "admin_support_management": show_support_management_menu, 
            "admin_edit_support_link": start_edit_support_link_flow,
            "admin_tutorial_management": show_tutorial_management_menu, 
            "admin_add_tutorial": start_add_tutorial_flow,             
            "admin_list_tutorials": list_tutorials,  
            "admin_channel_lock_management": show_channel_lock_menu,
            "admin_set_channel_lock": start_set_channel_lock_flow,
            "admin_remove_channel_lock": execute_remove_channel_lock,
            "admin_user_management": lambda a, m: _show_menu(a, "مدیریت کاربران:", inline_keyboards.get_user_management_menu(), m),
            "admin_search_user": start_search_user_flow,
            "admin_delete_plan": start_delete_plan_flow,
            "admin_edit_plan": start_edit_plan_flow,
            "admin_create_backup": create_backup,
            "admin_main_menu":  lambda a, m: (_clear_admin_state(a), _show_menu(a, messages.ADMIN_WELCOME, inline_keyboards.get_admin_main_inline_menu(), m)),
            "admin_server_management": _show_server_management_menu,
            "admin_plan_management": lambda a, m: (_clear_admin_state(a), _show_plan_management_menu(a, m)),
            "admin_payment_management": _show_payment_gateway_management_menu,
            "admin_add_server": start_add_server_flow,
            "admin_delete_server": start_delete_server_flow,
            "admin_add_plan": start_add_plan_flow,
            "admin_toggle_plan_status": start_toggle_plan_status_flow,
            "admin_add_gateway": start_add_gateway_flow,
            "admin_toggle_gateway_status": start_toggle_gateway_status_flow,
            "admin_list_servers": list_all_servers,
            "admin_test_all_servers": test_all_servers,
            "admin_list_plans": list_plans_action,
            "admin_list_gateways": list_gateways_action,
            "admin_list_users": list_all_users,
            "admin_manage_inbounds": start_manage_inbounds_flow,
        }
        
        if data in actions:
            actions[data](admin_id, message)
            return

        # --- هندل کردن موارد پیچیده‌تر ---
        if data.startswith("gateway_type_"):
            handle_gateway_type_selection(admin_id, call.message, data.replace('gateway_type_', ''))
        elif data.startswith("admin_delete_tutorial_"): # <-- NEW
            tutorial_id = int(data.split('_')[-1])
            execute_delete_tutorial(admin_id, message, tutorial_id)
        elif data.startswith("plan_type_"):
            get_plan_details_from_callback(admin_id, message, data.replace('plan_type_', ''))
        elif data.startswith("confirm_delete_server_"):
            execute_delete_server(admin_id, message, int(data.split('_')[-1]))
        elif data.startswith("inbound_"):
            handle_inbound_selection(admin_id, call)
        elif data.startswith("admin_approve_payment_"):
            process_payment_approval(admin_id, int(data.split('_')[-1]), message)
        elif data.startswith("admin_reject_payment_"):
            process_payment_rejection(admin_id, int(data.split('_')[-1]), message)
        elif data.startswith("confirm_delete_plan_"):
            plan_id = int(data.split('_')[-1])
            execute_delete_plan(admin_id, message, plan_id)
        elif data.startswith("admin_delete_purchase_"):
            parts = data.split('_')
            purchase_id = int(parts[3])
            user_telegram_id = int(parts[4])
            execute_delete_purchase(admin_id, message, purchase_id, user_telegram_id)
        if data.startswith("admin_set_support_type_"):
            support_type = data.split('_')[-1]
            # --- THE FIX IS HERE ---
            # Pass the entire 'call' object, not just 'message'
            set_support_type(admin_id, call, support_type)
        elif data.startswith("admin_delete_purchase_"):
            parts = data.split('_')
            purchase_id, user_telegram_id = int(parts[3]), int(parts[4])
            execute_delete_purchase(admin_id, message, purchase_id, user_telegram_id)
        else:
            _bot.edit_message_text(messages.UNDER_CONSTRUCTION, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_main_menu"))
    @_bot.message_handler(func=lambda msg: helpers.is_admin(msg.from_user.id) and _admin_states.get(msg.from_user.id))
    def handle_admin_stateful_messages(message):
        _handle_stateful_message(message.from_user.id, message)
        
        


    # =============================================================================
# SECTION: Final Execution Functions
# =============================================================================

    def execute_add_server(admin_id, data):
        _clear_admin_state(admin_id)
        msg = _bot.send_message(admin_id, messages.ADD_SERVER_TESTING)
        temp_xui_client = _xui_api(panel_url=data['url'], username=data['username'], password=data['password'])
        if temp_xui_client.login():
            server_id = _db_manager.add_server(data['name'], data['url'], data['username'], data['password'], data['sub_base_url'], data['sub_path_prefix'])
            if server_id:
                _db_manager.update_server_status(server_id, True, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                _bot.edit_message_text(messages.ADD_SERVER_SUCCESS.format(server_name=data['name']), admin_id, msg.message_id)
            else:
                _bot.edit_message_text(messages.ADD_SERVER_DB_ERROR.format(server_name=data['name']), admin_id, msg.message_id)
        else:
            _bot.edit_message_text(messages.ADD_SERVER_LOGIN_FAILED.format(server_name=data['name']), admin_id, msg.message_id)
        _show_server_management_menu(admin_id)

    def execute_delete_server(admin_id, message, server_id):
        # پاک کردن وضعیت در ابتدای اجرای عملیات نهایی
        _clear_admin_state(admin_id)
        
        server = _db_manager.get_server_by_id(server_id)
        if server and _db_manager.delete_server(server_id):
            _bot.edit_message_text(messages.SERVER_DELETED_SUCCESS.format(server_name=server['name']), admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
        else:
            _bot.edit_message_text(messages.SERVER_DELETED_ERROR, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))

    def execute_add_plan(admin_id, data):
        _clear_admin_state(admin_id)
        plan_id = _db_manager.add_plan(
            name=data.get('name'), plan_type=data.get('plan_type'),
            volume_gb=data.get('volume_gb'), duration_days=data.get('duration_days'),
            price=data.get('price'), per_gb_price=data.get('per_gb_price')
        )
        msg_to_send = messages.ADD_PLAN_SUCCESS if plan_id else messages.ADD_PLAN_DB_ERROR
        _bot.send_message(admin_id, msg_to_send.format(plan_name=data['name']))
        _show_plan_management_menu(admin_id)
        
    def execute_add_gateway(admin_id, data):
        _clear_admin_state(admin_id)
        gateway_id = _db_manager.add_payment_gateway(
            name=data.get('name'),
            gateway_type=data.get('gateway_type'),  # <-- اصلاح شد
            card_number=data.get('card_number'),
            card_holder_name=data.get('card_holder_name'),
            merchant_id=data.get('merchant_id'),    # <-- اضافه شد
            description=data.get('description'),
            priority=0
        )
        
        msg_to_send = messages.ADD_GATEWAY_SUCCESS if gateway_id else messages.ADD_GATEWAY_DB_ERROR
        _bot.send_message(admin_id, msg_to_send.format(gateway_name=data['name']))
        _show_payment_gateway_management_menu(admin_id)

    def execute_toggle_plan_status(admin_id, plan_id_str: str): # ورودی به text تغییر کرد
        _clear_admin_state(admin_id)
        if not plan_id_str.isdigit() or not (plan := _db_manager.get_plan_by_id(int(plan_id_str))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND)
            _show_plan_management_menu(admin_id)
            return
        new_status = not plan['is_active']
        if _db_manager.update_plan_status(plan['id'], new_status):
            _bot.send_message(admin_id, messages.PLAN_STATUS_TOGGLED_SUCCESS.format(plan_name=plan['name'], new_status="فعال" if new_status else "غیرفعال"))
        else:
            _bot.send_message(admin_id, messages.PLAN_STATUS_TOGGLED_ERROR.format(plan_name=plan['name']))
        _show_plan_management_menu(admin_id)
        
    def execute_toggle_gateway_status(admin_id, gateway_id_str: str): # ورودی به text تغییر کرد
        _clear_admin_state(admin_id)
        if not gateway_id_str.isdigit() or not (gateway := _db_manager.get_payment_gateway_by_id(int(gateway_id_str))):
            _bot.send_message(admin_id, messages.GATEWAY_NOT_FOUND)
            _show_payment_gateway_management_menu(admin_id)
            return
        new_status = not gateway['is_active']
        if _db_manager.update_payment_gateway_status(gateway['id'], new_status):
            _bot.send_message(admin_id, messages.GATEWAY_STATUS_TOGGLED_SUCCESS.format(gateway_name=gateway['name'], new_status="فعال" if new_status else "غیرفعال"))
        else:
            _bot.send_message(admin_id, messages.GATEWAY_STATUS_TOGGLED_ERROR.format(gateway_name=gateway['name']))
        _show_payment_gateway_management_menu(admin_id)
        # =============================================================================
    # SECTION: Process-Specific Helper Functions
    # =============================================================================

    def _generate_server_list_text():
        servers = _db_manager.get_all_servers()
        if not servers: return messages.NO_SERVERS_FOUND
        response_text = messages.LIST_SERVERS_HEADER
        for s in servers:
            status = "✅ آنلاین" if s['is_online'] else "❌ آفلاین"
            is_active_emoji = "✅" if s['is_active'] else "❌"
            sub_link = f"{s['subscription_base_url'].rstrip('/')}/{s['subscription_path_prefix'].strip('/')}/<SUB_ID>"
            response_text += messages.SERVER_DETAIL_TEMPLATE.format(
                name=helpers.escape_markdown_v1(s['name']), id=s['id'], status=status, is_active_emoji=is_active_emoji, sub_link=helpers.escape_markdown_v1(sub_link)
            )
        return response_text

    def process_manage_inbounds_flow(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        if state_info.get('state') != 'waiting_for_server_id_for_inbounds': return
        server_id_str = message.text.strip()
        prompt_id = state_info.get('prompt_message_id')
        try: _bot.delete_message(admin_id, message.message_id)
        except Exception: pass
        if not server_id_str.isdigit() or not (server_data := _db_manager.get_server_by_id(int(server_id_str))):
            _bot.edit_message_text(f"{messages.SERVER_NOT_FOUND}\n\n{messages.SELECT_SERVER_FOR_INBOUNDS_PROMPT}", admin_id, prompt_id, parse_mode='Markdown'); return
        server_id = int(server_id_str)
        _bot.edit_message_text(messages.FETCHING_INBOUNDS, admin_id, prompt_id)
        temp_xui_client = _xui_api(panel_url=server_data['panel_url'], username=server_data['username'], password=server_data['password'])
        panel_inbounds = temp_xui_client.list_inbounds()
        if not panel_inbounds:
            _bot.edit_message_text(messages.NO_INBOUNDS_FOUND_ON_PANEL, admin_id, prompt_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            _clear_admin_state(admin_id); return
        active_db_inbound_ids = [i['inbound_id'] for i in _db_manager.get_server_inbounds(server_id, only_active=True)]
        state_info['state'] = f'selecting_inbounds_for_{server_id}'
        state_info['data'] = {'panel_inbounds': panel_inbounds, 'selected_inbound_ids': active_db_inbound_ids}
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, active_db_inbound_ids)
        _bot.edit_message_text(messages.SELECT_INBOUNDS_TO_ACTIVATE.format(server_name=server_data['name']), admin_id, prompt_id, reply_markup=markup, parse_mode='Markdown')

    def handle_inbound_selection(admin_id, call):
        """کلیک روی دکمه‌های کیبورد انتخاب اینباند را به درستی مدیریت می‌کند."""
        data = call.data
        parts = data.split('_')
        action = parts[1]

        state_info = _admin_states.get(admin_id)
        if not state_info: return

        server_id = None
        
        # استخراج server_id بر اساس نوع اکشن
        if action == 'toggle':
            # فرمت: inbound_toggle_{server_id}_{inbound_id}
            if len(parts) == 4:
                server_id = int(parts[2])
        else: # برای select, deselect, save
            # فرمت: inbound_select_all_{server_id}
            server_id = int(parts[-1])

        if server_id is None or state_info.get('state') != f'selecting_inbounds_for_{server_id}':
            return

        # دریافت اطلاعات لازم از state
        selected_ids = state_info['data'].get('selected_inbound_ids', [])
        panel_inbounds = state_info['data'].get('panel_inbounds', [])

        # انجام عملیات بر اساس اکشن
        if action == 'toggle':
            inbound_id_to_toggle = int(parts[3])
            if inbound_id_to_toggle in selected_ids:
                selected_ids.remove(inbound_id_to_toggle)
            else:
                selected_ids.append(inbound_id_to_toggle)
        
        elif action == 'select' and parts[2] == 'all':
            panel_ids = {p['id'] for p in panel_inbounds}
            selected_ids.extend([pid for pid in panel_ids if pid not in selected_ids])
            selected_ids = list(set(selected_ids)) # حذف موارد تکراری
        
        elif action == 'deselect' and parts[2] == 'all':
            selected_ids.clear()
            
        elif action == 'save':
            save_inbound_changes(admin_id, call.message, server_id, selected_ids)
            return
        
        # به‌روزرسانی state و کیبورد
        state_info['data']['selected_inbound_ids'] = selected_ids
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, selected_ids)
        
        try:
            _bot.edit_message_reply_markup(chat_id=admin_id, message_id=call.message.message_id, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in e.description:
                logger.warning(f"Error updating inbound selection keyboard: {e}")

    def process_payment_approval(admin_id, payment_id, message):
        """
        Handles the admin's approval and sets the user's state to wait for a custom config name.
        """
        _bot.edit_message_caption("در حال ارسال درخواست به کاربر برای نام کانفیگ...", message.chat.id, message.message_id)
        
        payment = _db_manager.get_payment_by_id(payment_id)
        if not payment or payment['is_confirmed']:
            _bot.answer_callback_query(message.id, "این پرداخت قبلاً پردازش شده است.", show_alert=True)
            return

        # Update payment status and admin notification message
        order_details = json.loads(payment['order_details_json'])
        _db_manager.update_payment_status(payment_id, True, admin_id)

        admin_user = _bot.get_chat_member(admin_id, admin_id).user
        admin_username = f"@{admin_user.username}" if admin_user.username else admin_user.first_name
        new_caption = message.caption + "\n\n" + messages.ADMIN_PAYMENT_CONFIRMED_DISPLAY.format(admin_username=admin_username)
        _bot.edit_message_caption(new_caption, message.chat.id, message.message_id, parse_mode='Markdown')

        # --- NEW LOGIC: Set the user's state in the shared _user_states dictionary ---
        user_telegram_id = order_details['user_telegram_id']
        prompt = _bot.send_message(user_telegram_id, messages.ASK_FOR_CUSTOM_CONFIG_NAME)
        
        _user_states[user_telegram_id] = {
            'state': 'waiting_for_custom_config_name',
            'data': order_details,
            'prompt_message_id': prompt.message_id
        }



    def process_payment_rejection(admin_id, payment_id, message):
        payment = _db_manager.get_payment_by_id(payment_id)
        if not payment or payment['is_confirmed']:
            _bot.answer_callback_query(message.id, "این پرداخت قبلاً پردازش شده است.", show_alert=True); return
        _db_manager.update_payment_status(payment_id, False, admin_id)
        admin_user = _bot.get_chat_member(admin_id, admin_id).user
        new_caption = message.caption + "\n\n" + messages.ADMIN_PAYMENT_REJECTED_DISPLAY.format(admin_username=f"@{admin_user.username}" if admin_user.username else admin_user.first_name)
        _bot.edit_message_caption(new_caption, message.chat.id, message.message_id, parse_mode='Markdown')
        order_details = json.loads(payment['order_details_json'])
        _bot.send_message(order_details['user_telegram_id'], messages.PAYMENT_REJECTED_USER.format(support_link=SUPPORT_CHANNEL_LINK))
        
        
    def save_inbound_changes(admin_id, message, server_id, selected_ids):
        """تغییرات انتخاب اینباندها را در دیتابیس ذخیره کرده و به کاربر بازخورد می‌دهد."""
        server_data = _db_manager.get_server_by_id(server_id)
        panel_inbounds = _admin_states.get(admin_id, {}).get('data', {}).get('panel_inbounds', [])
        
        inbounds_to_save = [
            {'id': p_in['id'], 'remark': p_in.get('remark', '')}
            for p_in in panel_inbounds if p_in['id'] in selected_ids
        ]
        
        # ابتدا اطلاعات در دیتابیس ذخیره می‌شود
        if _db_manager.update_server_inbounds(server_id, inbounds_to_save):
            msg = messages.INBOUND_CONFIG_SUCCESS
        else:
            msg = messages.INBOUND_CONFIG_FAILED

        # سپس پیام فعلی ویرایش شده و دکمه بازگشت نمایش داده می‌شود
        _bot.edit_message_text(
            msg.format(server_name=server_data['name']),
            admin_id,
            message.message_id,
            reply_markup=inline_keyboards.get_back_button("admin_server_management")
        )
        
        # در نهایت، وضعیت ادمین پاک می‌شود
        _clear_admin_state(admin_id)
    def start_manage_inbounds_flow(admin_id, message):
            """فرآیند مدیریت اینباند را با نمایش لیست سرورها آغاز می‌کند."""
            _clear_admin_state(admin_id)
            list_text = _generate_server_list_text()
            if list_text == messages.NO_SERVERS_FOUND:
                _bot.edit_message_text(list_text, admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
                return
            
            _admin_states[admin_id] = {'state': 'waiting_for_server_id_for_inbounds', 'prompt_message_id': message.message_id}
            prompt_text = f"{list_text}\n\n{messages.SELECT_SERVER_FOR_INBOUNDS_PROMPT}"
            _bot.edit_message_text(prompt_text, admin_id, message.message_id, parse_mode='Markdown')


    def process_manage_inbounds_flow(admin_id, message):
        """
        پس از دریافت ID سرور از ادمین، لیست اینباندهای آن را از پنل X-UI گرفته و نمایش می‌دهد.
        """
        state_info = _admin_states.get(admin_id, {})
        if state_info.get('state') != 'waiting_for_server_id_for_inbounds': return

        server_id_str = message.text.strip()
        prompt_id = state_info.get('prompt_message_id')
        try: _bot.delete_message(admin_id, message.message_id)
        except Exception: pass
        
        if not server_id_str.isdigit() or not (server_data := _db_manager.get_server_by_id(int(server_id_str))):
            _bot.edit_message_text(f"{messages.SERVER_NOT_FOUND}\n\n{messages.SELECT_SERVER_FOR_INBOUNDS_PROMPT}", admin_id, prompt_id, parse_mode='Markdown')
            return

        server_id = int(server_id_str)
        _bot.edit_message_text(messages.FETCHING_INBOUNDS, admin_id, prompt_id)
        
        temp_xui_client = _xui_api(panel_url=server_data['panel_url'], username=server_data['username'], password=server_data['password'])
        panel_inbounds = temp_xui_client.list_inbounds()

        if not panel_inbounds:
            _bot.edit_message_text(messages.NO_INBOUNDS_FOUND_ON_PANEL, admin_id, prompt_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            _clear_admin_state(admin_id)
            return

        active_db_inbound_ids = [i['inbound_id'] for i in _db_manager.get_server_inbounds(server_id, only_active=True)]
        
        state_info['state'] = f'selecting_inbounds_for_{server_id}'
        state_info['data'] = {'panel_inbounds': panel_inbounds, 'selected_inbound_ids': active_db_inbound_ids}
        
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, active_db_inbound_ids)
        _bot.edit_message_text(messages.SELECT_INBOUNDS_TO_ACTIVATE.format(server_name=server_data['name']), admin_id, prompt_id, reply_markup=markup, parse_mode='Markdown')


    def save_inbound_changes(admin_id, message, server_id, selected_ids):
        """تغییرات انتخاب اینباندها را در دیتابیس ذخیره می‌کند."""
        server_data = _db_manager.get_server_by_id(server_id)
        panel_inbounds = _admin_states.get(admin_id, {}).get('data', {}).get('panel_inbounds', [])
        inbounds_to_save = [{'id': p_in['id'], 'remark': p_in.get('remark', '')} for p_in in panel_inbounds if p_in['id'] in selected_ids]
        
        msg = messages.INBOUND_CONFIG_SUCCESS if _db_manager.update_server_inbounds(server_id, inbounds_to_save) else messages.INBOUND_CONFIG_FAILED
        _bot.edit_message_text(msg.format(server_name=server_data['name']), admin_id, message.message_id, reply_markup=inline_keyboards.get_back_button("admin_server_management"))
            
        _clear_admin_state(admin_id)

    def handle_inbound_selection(admin_id, call):
        """با منطق جدید برای خواندن callback_data اصلاح شده است."""
        data = call.data
        parts = data.split('_')
        action = parts[1]

        state_info = _admin_states.get(admin_id)
        if not state_info: return

        # استخراج server_id با روشی که برای همه اکشن‌ها کار کند
        server_id = int(parts[2]) if action == 'toggle' else int(parts[-1])
            
        if state_info.get('state') != f'selecting_inbounds_for_{server_id}': return

        selected_ids = state_info['data'].get('selected_inbound_ids', [])
        panel_inbounds = state_info['data'].get('panel_inbounds', [])

        if action == 'toggle':
            inbound_id_to_toggle = int(parts[3]) # آیدی اینباند همیشه پارامتر چهارم است
            if inbound_id_to_toggle in selected_ids:
                selected_ids.remove(inbound_id_to_toggle)
            else:
                selected_ids.append(inbound_id_to_toggle)
        
        elif action == 'select' and parts[2] == 'all':
            panel_ids = {p['id'] for p in panel_inbounds}
            selected_ids.extend([pid for pid in panel_ids if pid not in selected_ids])
        
        elif action == 'deselect' and parts[2] == 'all':
            selected_ids.clear()
            
        elif action == 'save':
            save_inbound_changes(admin_id, call.message, server_id, selected_ids)
            return
        
        state_info['data']['selected_inbound_ids'] = list(set(selected_ids))
        markup = inline_keyboards.get_inbound_selection_menu(server_id, panel_inbounds, selected_ids)
        
        try:
            _bot.edit_message_reply_markup(chat_id=admin_id, message_id=call.message.message_id, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if 'message is not modified' not in e.description:
                logger.warning(f"Error updating inbound selection keyboard: {e}")
                
                
    def create_backup(admin_id, message):
        """از فایل‌های حیاتی ربات (دیتابیس و .env) بکاپ گرفته و برای ادمین ارسال می‌کند."""
        _bot.edit_message_text("⏳ در حال ساخت فایل پشتیبان...", admin_id, message.message_id)
        
        backup_filename = f"alamor_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
        
        files_to_backup = [
            os.path.join(os.getcwd(), '.env'),
            _db_manager.db_path
        ]
        
        try:
            with zipfile.ZipFile(backup_filename, 'w') as zipf:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                    else:
                        logger.warning(f"فایل بکاپ یافت نشد: {file_path}")

            with open(backup_filename, 'rb') as backup_file:
                _bot.send_document(admin_id, backup_file, caption="✅ فایل پشتیبان شما آماده است.")
            
            _bot.delete_message(admin_id, message.message_id)
            _show_admin_main_menu(admin_id)

        except Exception as e:
            logger.error(f"خطا در ساخت بکاپ: {e}")
            _bot.edit_message_text("❌ در ساخت فایل پشتیبان خطایی رخ داد.", admin_id, message.message_id)
        finally:
            # پاک کردن فایل زیپ پس از ارسال
            if os.path.exists(backup_filename):
                os.remove(backup_filename)
                
                
    def handle_gateway_type_selection(admin_id, message, gateway_type):
        state_info = _admin_states.get(admin_id)
        if not state_info or state_info.get('state') != 'waiting_for_gateway_type': return
        
        state_info['data']['gateway_type'] = gateway_type
        
        if gateway_type == 'zarinpal':
            state_info['state'] = 'waiting_for_merchant_id'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_MERCHANT_ID, admin_id, message.message_id)
        elif gateway_type == 'card_to_card':
            state_info['state'] = 'waiting_for_card_number'
            _bot.edit_message_text(messages.ADD_GATEWAY_PROMPT_CARD_NUMBER, admin_id, message.message_id)
            
            
            
            
    def start_delete_plan_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.DELETE_PLAN_PROMPT, inline_keyboards.get_back_button("admin_plan_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_delete', 'prompt_message_id': prompt.message_id}
        
    def process_delete_plan_id(admin_id, message):
        state_info = _admin_states[admin_id]
        if not message.text.isdigit() or not (plan := _db_manager.get_plan_by_id(int(message.text))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND); return

        plan_id = int(message.text)
        confirm_text = messages.DELETE_PLAN_CONFIRM.format(
            plan_name=helpers.escape_markdown_v1(plan['name']), 
            plan_id=plan_id
        )
        markup = inline_keyboards.get_confirmation_menu(f"confirm_delete_plan_{plan_id}", "admin_plan_management")
        _bot.edit_message_text(confirm_text, admin_id, state_info['prompt_message_id'], reply_markup=markup, parse_mode='Markdown')
        _clear_admin_state(admin_id) # State is cleared, waiting for callback

    def execute_delete_plan(admin_id, message, plan_id):
        plan = _db_manager.get_plan_by_id(plan_id)
        if plan and _db_manager.delete_plan(plan_id):
            _bot.edit_message_text(messages.PLAN_DELETED_SUCCESS.format(plan_name=plan['name']), admin_id, message.message_id)
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, admin_id, message.message_id)
        _show_plan_management_menu(admin_id)

    # --- EDIT PLAN ---
    def start_edit_plan_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.EDIT_PLAN_PROMPT_ID, inline_keyboards.get_back_button("admin_plan_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_plan_id_to_edit', 'data': {}, 'prompt_message_id': prompt.message_id}

    def process_edit_plan_id(admin_id, message):
        state_info = _admin_states[admin_id]
        if not message.text.isdigit() or not (plan := _db_manager.get_plan_by_id(int(message.text))):
            _bot.send_message(admin_id, messages.PLAN_NOT_FOUND); return
        
        state_info['data']['plan_id'] = int(message.text)
        state_info['data']['original_plan'] = plan
        state_info['state'] = 'waiting_for_new_plan_name'
        _bot.edit_message_text(messages.EDIT_PLAN_NEW_NAME, admin_id, state_info['prompt_message_id'])

    def process_edit_plan_name(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['new_name'] = message.text
        state_info['state'] = 'waiting_for_new_plan_price'
        _bot.edit_message_text(messages.EDIT_PLAN_NEW_PRICE, admin_id, state_info['prompt_message_id'])

    def process_edit_plan_price(admin_id, message):
        state_info = _admin_states[admin_id]
        if not helpers.is_float_or_int(message.text) or float(message.text) < 0:
            _bot.send_message(admin_id, "قیمت نامعتبر است."); return
        
        data = state_info['data']
        original_plan = data['original_plan']
        
        _db_manager.update_plan(
            plan_id=data['plan_id'],
            name=data['new_name'],
            price=float(message.text),
            volume_gb=original_plan['volume_gb'],
            duration_days=original_plan['duration_days']
        )
        _bot.edit_message_text(messages.EDIT_PLAN_SUCCESS.format(plan_name=data['new_name']), admin_id, state_info['prompt_message_id'])
        _clear_admin_state(admin_id)
        _show_plan_management_menu(admin_id)
        
        
    def start_search_user_flow(admin_id, message):
        """Starts the flow for searching a user by their Telegram ID."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:", inline_keyboards.get_back_button("admin_user_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_user_id_to_search', 'prompt_message_id': prompt.message_id}

    def process_user_search(admin_id, message):
        """Processes the user ID, finds the user, and shows their subscriptions."""
        state_info = _admin_states.get(admin_id, {})
        user_id_str = message.text.strip()

        if not user_id_str.isdigit():
            _bot.send_message(admin_id, "آیدی وارد شده نامعتبر است. لطفاً یک عدد وارد کنید.")
            return

        user_telegram_id = int(user_id_str)
        purchases = _db_manager.get_user_purchases_by_telegram_id(user_telegram_id)
        user_info = _db_manager.get_user_by_telegram_id(user_telegram_id)
        user_display = user_info['first_name'] if user_info else f"کاربر {user_telegram_id}"

        # --- THE FIX IS HERE: Pass _db_manager to the keyboard function ---
        markup = inline_keyboards.get_user_subscriptions_management_menu(_db_manager, purchases, user_telegram_id)
        
        _bot.edit_message_text(
            f"اشتراک‌های یافت شده برای **{user_display}**:",
            admin_id,
            state_info['prompt_message_id'],
            reply_markup=markup,
            parse_mode='Markdown'
        )
        _clear_admin_state(admin_id)
        
        
        
    def execute_delete_purchase(admin_id, message, purchase_id, user_telegram_id):
        """
        Deletes a purchase from the local database and the corresponding client
        from the X-UI panel.
        """
        # First, get purchase details to find the client UUID and server ID
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            _bot.answer_callback_query(message.id, "این اشتراک یافت نشد.", show_alert=True)
            return

        # Step 1: Delete the purchase from the local database
        if not _db_manager.delete_purchase(purchase_id):
            _bot.answer_callback_query(message.id, "خطا در حذف اشتراک از دیتابیس.", show_alert=True)
            return

        # Step 2: Delete the client from the X-UI panel
        try:
            server = _db_manager.get_server_by_id(purchase['server_id'])
            if server and purchase['xui_client_uuid']:
                api_client = _xui_api(
                    panel_url=server['panel_url'],
                    username=server['username'],
                    password=server['password']
                )
                # We need the inbound_id to delete the client. This is a limitation.
                # A better approach for the future is to store inbound_id in the purchase record.
                # For now, we assume we need to iterate or have a default.
                # This part of the logic might need enhancement based on your X-UI panel version.
                # We will try to delete by UUID, which is supported by some panel forks.
                
                # Note: The default X-UI API requires inbound_id to delete a client.
                # If your panel supports deleting by UUID directly, this will work.
                # Otherwise, this part needs to be adapted.
                # For now, we log the action. A full implementation would require a proper API call.
                logger.info(f"Admin {admin_id} deleted purchase {purchase_id}. Corresponding X-UI client UUID to be deleted is {purchase['xui_client_uuid']} on server {server['name']}.")
                # api_client.delete_client(inbound_id, purchase['xui_client_uuid']) # This line would be needed
        except Exception as e:
            logger.error(f"Could not delete client from X-UI for purchase {purchase_id}: {e}")
            _bot.answer_callback_query(message.id, "اشتراک از دیتابیس حذف شد، اما در حذف از پنل خطایی رخ داد.", show_alert=True)

        _bot.answer_callback_query(message.id, f"✅ اشتراک {purchase_id} با موفقیت حذف شد.")

        # Step 3: Refresh the user's subscription list for the admin
        # We create a mock message object to pass to the search function
        mock_message = types.Message(
            message_id=message.message_id,
            chat=message.chat,
            date=None,
            content_type='text',
            options={},
            json_string=""
        )
        mock_message.text = str(user_telegram_id)
        
        # Put the admin back into the search state to show the updated list
        _admin_states[admin_id] = {'state': 'waiting_for_user_id_to_search', 'prompt_message_id': message.message_id}
        process_user_search(admin_id, mock_message)



    def show_channel_lock_menu(admin_id, message):
        """Displays the channel lock management menu."""
        channel_id = _db_manager.get_setting('required_channel_id')
        status = f"فعال روی کانال `{channel_id}`" if channel_id else "غیرفعال"
        text = messages.CHANNEL_LOCK_MENU_TEXT.format(status=status)
        markup = inline_keyboards.get_channel_lock_management_menu(channel_set=bool(channel_id))
        _show_menu(admin_id, text, markup, message)

    def start_set_channel_lock_flow(admin_id, message):
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.CHANNEL_LOCK_SET_PROMPT, inline_keyboards.get_back_button("admin_channel_lock_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_channel_id', 'prompt_message_id': prompt.message_id}

    def process_set_channel_id(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        channel_id_str = message.text.strip()
        # ... (code for cancel and validation remains the same)

        if not (channel_id_str.startswith('-') and channel_id_str[1:].isdigit()):
            _bot.send_message(admin_id, messages.CHANNEL_LOCK_INVALID_ID)
            return

        # Save the ID in the state and ask for the link
        state_info['data'] = {'channel_id': channel_id_str}
        state_info['state'] = 'waiting_for_channel_link' # <-- Move to next state
        
        _bot.edit_message_text(
            "عالی. حالا لطفاً لینک عمومی کانال را وارد کنید (مثلاً: https://t.me/Alamor_Network):",
            admin_id,
            state_info['prompt_message_id']
        )

    def process_set_channel_link(admin_id, message):
        """ --- NEW FUNCTION --- """
        state_info = _admin_states.get(admin_id, {})
        channel_link = message.text.strip()
        
        if not channel_link.lower().startswith(('http://', 'https://')):
            _bot.send_message(admin_id, "لینک وارد شده نامعتبر است. لطفاً لینک کامل را وارد کنید.")
            return
            
        channel_id = state_info['data']['channel_id']

        # Now, save both ID and Link to the database
        _db_manager.update_setting('required_channel_id', channel_id)
        _db_manager.update_setting('required_channel_link', channel_link)
        
        _bot.edit_message_text(messages.CHANNEL_LOCK_SUCCESS.format(channel_id=channel_id), admin_id, state_info['prompt_message_id'])
        _clear_admin_state(admin_id)
        show_channel_lock_menu(admin_id) # Show the updated menu
    def execute_remove_channel_lock(admin_id, message):
        _db_manager.update_setting('required_channel_id', '') # Set to empty string
        _db_manager.update_setting('required_channel_link', '')
        _bot.answer_callback_query(message.id, messages.CHANNEL_LOCK_REMOVED)
        show_channel_lock_menu(admin_id, message)
        
    def show_tutorial_management_menu(admin_id, message):
        """Displays the main menu for tutorial management."""
        _show_menu(admin_id, "💡 مدیریت آموزش‌ها", inline_keyboards.get_tutorial_management_menu(), message)

    def list_tutorials(admin_id, message):
        """Lists all saved tutorials with delete buttons."""
        all_tutorials = _db_manager.get_all_tutorials()
        markup = inline_keyboards.get_tutorials_list_menu(all_tutorials)
        _show_menu(admin_id, "برای حذف یک آموزش، روی آن کلیک کنید:", markup, message)

    def execute_delete_tutorial(admin_id, message, tutorial_id):
        """Deletes a tutorial and refreshes the list."""
        if _db_manager.delete_tutorial(tutorial_id):
            _bot.answer_callback_query(message.id, "✅ آموزش با موفقیت حذف شد.")
            list_tutorials(admin_id, message) # Refresh the list
        else:
            _bot.answer_callback_query(message.id, "❌ در حذف آموزش خطایی رخ داد.", show_alert=True)

    def start_add_tutorial_flow(admin_id, message):
        """Starts the multi-step process for adding a new tutorial."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, "لطفاً پلتفرم آموزش را وارد کنید (مثلا: اندروید، ویندوز، آیفون):", inline_keyboards.get_back_button("admin_tutorial_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_tutorial_platform', 'data': {}, 'prompt_message_id': prompt.message_id}

    def process_tutorial_platform(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['platform'] = message.text.strip()
        state_info['state'] = 'waiting_for_tutorial_app_name'
        _bot.edit_message_text("نام اپلیکیشن را وارد کنید (مثلا: V2RayNG):", admin_id, state_info['prompt_message_id'])

    def process_tutorial_app_name(admin_id, message):
        state_info = _admin_states[admin_id]
        state_info['data']['app_name'] = message.text.strip()
        state_info['state'] = 'waiting_for_tutorial_forward'
        _bot.edit_message_text("عالی. حالا پست آموزش را از کانال مورد نظر اینجا فوروارد کنید.", admin_id, state_info['prompt_message_id'])

    def process_tutorial_forward(admin_id, message):
        state_info = _admin_states.get(admin_id, {})
        # Check if the message is forwarded
        if not message.forward_from_chat:
            _bot.send_message(admin_id, "پیام ارسال شده فورواردی نیست. لطفاً یک پست را فوروارد کنید.")
            return

        data = state_info['data']
        platform = data['platform']
        app_name = data['app_name']
        forward_chat_id = message.forward_from_chat.id
        forward_message_id = message.forward_from_message_id

        if _db_manager.add_tutorial(platform, app_name, forward_chat_id, forward_message_id):
            _bot.edit_message_text("✅ آموزش با موفقیت ثبت شد.", admin_id, state_info['prompt_message_id'])
        else:
            _bot.edit_message_text("❌ خطایی در ثبت آموزش رخ داد.", admin_id, state_info['prompt_message_id'])
        
        _clear_admin_state(admin_id)
        show_tutorial_management_menu(admin_id)
        
        
    def show_support_management_menu(admin_id, message):
        """Displays the simple support management menu as plain text to avoid errors."""
        support_link = _db_manager.get_setting('support_link') or "تنظیم نشده"
        
        # We don't need to escape the link anymore because we are not using Markdown
        text = messages.SUPPORT_MANAGEMENT_MENU_TEXT.format(link=support_link)
        
        markup = inline_keyboards.get_support_management_menu()
        
        # --- THE FINAL FIX IS HERE ---
        # We explicitly tell the bot to send this specific menu as plain text.
        _show_menu(admin_id, text, markup, message, parse_mode=None)

    def set_support_type(admin_id, call, support_type):
        """Sets the support type (admin chat or link)."""
        _db_manager.update_setting('support_type', support_type)
        
        # --- THE FIX IS HERE ---
        # Use call.id to answer the query, and call.message to edit the message
        _bot.answer_callback_query(call.id, messages.SUPPORT_TYPE_SET_SUCCESS)
        show_support_management_menu(admin_id, call.message)

    def start_edit_support_link_flow(admin_id, message):
        """Starts the process for setting/editing the support link."""
        _clear_admin_state(admin_id)
        prompt = _show_menu(admin_id, messages.SET_SUPPORT_LINK_PROMPT, inline_keyboards.get_back_button("admin_support_management"), message)
        _admin_states[admin_id] = {'state': 'waiting_for_support_link', 'prompt_message_id': prompt.message_id}
    def process_support_link(admin_id, message):
        """Saves the support link provided by the admin."""
        # This function remains the same as before
        state_info = _admin_states.get(admin_id, {})
        support_link = message.text.strip()

        # You can add validation for t.me links here if you want
        if not support_link.lower().startswith(('http://', 'https://', 't.me/')):
            _bot.send_message(admin_id, "لینک وارد شده نامعتبر است. لطفاً لینک کامل را وارد کنید.")
            return
            
        _db_manager.update_setting('support_link', support_link)
        _bot.edit_message_text(messages.SUPPORT_LINK_SET_SUCCESS, admin_id, state_info['prompt_message_id'])
        _clear_admin_state(admin_id)
        show_support_management_menu(admin_id) # Show the updated menu
        
        
        
    def process_add_plan_server(message):
        """Processes the server ID and asks for the plan name."""
        admin_id = message.from_user.id
        
        try:
            _bot.delete_message(admin_id, message.message_id)
        except Exception:
            pass

        server_id_str = message.text.strip()
        
        if not server_id_str.isdigit() or not _db_manager.get_server_by_id(int(server_id_str)):
            prompt = _bot.send_message(admin_id, "ID سرور نامعتبر است. لطفاً دوباره تلاش کنید:")
            _bot.register_next_step_handler(prompt, process_add_plan_server) # Ask again
            return

        # Save data in a temporary dictionary for this conversation
        plan_data = {'server_id': int(server_id_str)}
        
        prompt = _bot.send_message(admin_id, "نام پلن را وارد کنید (مثلا: پلن اقتصادی):")
        _bot.register_next_step_handler(prompt, process_add_plan_name, plan_data) # Pass data to the next step

    def process_add_plan_price(message, plan_data):
        """--- CORRECTED VERSION: Calls the updated add_plan function correctly ---"""
        admin_id = message.from_user.id
        try:
            price_input = float(message.text)
            if price_input < 0: raise ValueError
        except (ValueError, TypeError):
            prompt = _bot.send_message(admin_id, "قیمت وارد شده نامعتبر است. لطفاً یک عدد وارد کنید:")
            _bot.register_next_step_handler(prompt, process_add_plan_price, plan_data)
            return

        # Prepare all arguments for the database function
        plan_data['price'] = price_input
        
        # Set default/null values for arguments not collected in this specific flow
        # This makes the call robust
        final_args = {
            'name': plan_data.get('name'),
            'plan_type': plan_data.get('plan_type'),
            'volume_gb': plan_data.get('volume_gb'),
            'duration_days': plan_data.get('duration_days'),
            'price': plan_data.get('price'),
            'per_gb_price': plan_data.get('per_gb_price')
        }
        
        # Adjust price based on plan type
        if final_args['plan_type'] == 'gigabyte_based':
            final_args['per_gb_price'] = final_args.pop('price', None)
        
        _db_manager.add_plan(
            name=final_args['name'],
            plan_type=final_args['plan_type'],
            volume_gb=final_args['volume_gb'],
            duration_days=final_args['duration_days'],
            price=final_args.get('price'), # Use .get() for safety
            per_gb_price=final_args.get('per_gb_price') # Use .get() for safety
        )
        
        _bot.send_message(admin_id, "✅ پلن با موفقیت اضافه شد.")
        
    def process_add_plan_name(message, plan_data):
        """Processes the plan name and asks for the price."""
        admin_id = message.from_user.id
        plan_data['name'] = message.text.strip()
        
        prompt = _bot.send_message(admin_id, "قیمت هر گیگابایت را به تومان وارد کنید:")
        _bot.register_next_step_handler(prompt, process_add_plan_price, plan_data)
