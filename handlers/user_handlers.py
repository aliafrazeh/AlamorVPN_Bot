import telebot
from telebot import types
import logging
import json
import qrcode
import datetime
from io import BytesIO
import uuid
import requests
from config import SUPPORT_CHANNEL_LINK, ADMIN_IDS
from database.db_manager import DatabaseManager
from api_client.xui_api_client import XuiAPIClient
from utils import messages, helpers
from keyboards import inline_keyboards
from utils.config_generator import ConfigGenerator
from utils.helpers import is_float_or_int , escape_markdown_v1
from config import ZARINPAL_MERCHANT_ID, WEBHOOK_DOMAIN , ZARINPAL_SANDBOX
from main import send_welcome
from utils.bot_helpers import send_subscription_info

logger = logging.getLogger(__name__)

# ماژول های سراسری
_bot: telebot.TeleBot = None
_db_manager: DatabaseManager = None
_xui_api: XuiAPIClient = None
_config_generator: ConfigGenerator = None
# متغیرهای وضعیت
_user_menu_message_ids = {} # {user_id: message_id}
_user_states = {} # {user_id: {'state': '...', 'data': {...}}}
def _show_menu(user_id, text, markup, message=None, parse_mode='Markdown'):
    """
    This function intelligently handles Markdown parsing errors.
    """
    try:
        if message:
            return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=parse_mode)
        else:
            return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)

    except telebot.apihelper.ApiTelegramException as e:
        if "can't parse entities" in str(e):
            logger.warning(f"Markdown parse error for user {user_id}. Retrying with plain text.")
            try:
                if message:
                    return _bot.edit_message_text(text, user_id, message.message_id, reply_markup=markup, parse_mode=None)
                else:
                    return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=None)
            except telebot.apihelper.ApiTelegramException as retry_e:
                logger.error(f"Failed to send menu even as plain text for user {user_id}: {retry_e}")

        elif 'message to edit not found' in str(e):
            return _bot.send_message(user_id, text, reply_markup=markup, parse_mode=parse_mode)
        elif 'message is not modified' not in str(e):
            logger.warning(f"Menu error for {user_id}: {e}")
            
    return message


ZARINPAL_API_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_STARTPAY_URL = "https://www.zarinpal.com/pg/StartPay/"

def register_user_handlers(bot_instance, db_manager_instance, xui_api_instance):
    global _bot, _db_manager, _xui_api, _config_generator
    _bot = bot_instance
    _db_manager = db_manager_instance
    _xui_api = xui_api_instance
    _config_generator = ConfigGenerator(db_manager_instance)

    # --- هندلرهای اصلی ---
    @_bot.callback_query_handler(func=lambda call: not call.from_user.is_bot and call.data.startswith('user_'))
    def handle_main_callbacks(call):
        """هندل کردن دکمه‌های منوی اصلی کاربر"""
        user_id = call.from_user.id
        _bot.answer_callback_query(call.id)
        # فقط در صورتی وضعیت را پاک کن که یک آیتم از منوی اصلی انتخاب شده باشد
        if call.data in ["user_main_menu", "user_buy_service", "user_my_services", "user_free_test", "user_support"]:
            _clear_user_state(user_id)

        data = call.data
        if data == "user_main_menu":
            _show_user_main_menu(user_id, message_to_edit=call.message)
        elif data == "user_buy_service":
            start_purchase(user_id, call.message)
        elif data == "user_my_services":
            show_my_services_list(user_id, call.message)
        elif data == "user_add_balance":
            start_add_balance_flow(user_id, call.message)
        # --- بخش اصلاح شده ---
        elif data == "user_free_test":
            # اکنون تابع ساخت اکانت تست فراخوانی می‌شود
            handle_free_test_request(user_id, call.message)
        # --- پایان بخش اصلاح شده ---

        elif data == "user_buy_profile": # <-- این بلاک را اضافه کنید
            start_profile_purchase(user_id, call.message)
        elif data == "user_support":
            _bot.edit_message_text(f"📞 برای پشتیبانی با ما در ارتباط باشید: {SUPPORT_CHANNEL_LINK}", user_id, call.message.message_id)
        elif data.startswith("user_service_details_"):
            purchase_id = int(data.replace("user_service_details_", ""))
            show_service_details(user_id, purchase_id, call.message)
        elif data.startswith("user_get_single_configs_"):
            purchase_id = int(data.replace("user_get_single_configs_", ""))
            send_single_configs(user_id, purchase_id)
        
        elif data == "user_how_to_connect":
            show_platform_selection(user_id, call.message)
        elif data.startswith("user_select_platform_"):
            platform = data.replace("user_select_platform_", "")
            show_apps_for_platform(user_id, platform, call.message)
        elif data.startswith("user_select_tutorial_"):
            tutorial_id = int(data.replace("user_select_tutorial_", ""))
            send_tutorial_to_user(user_id, tutorial_id, call.message)
        elif data == "user_account": 
            show_user_account_menu(user_id, call.message) 
        elif data == "user_check_join_status":
            required_channel_id_str = _db_manager.get_setting('required_channel_id')
            if required_channel_id_str:
                required_channel_id = int(required_channel_id_str)
                if helpers.is_user_member_of_channel(_bot, required_channel_id, call.from_user.id):
                    # User has joined, delete the message and show the main menu
                    _bot.delete_message(call.message.chat.id, call.message.message_id)
                    # We call the /start logic again, which will now succeed
                    from main import send_welcome 
                    send_welcome(call.message)
                else:
                    # User has not joined yet, show an alert
                    _bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید.", show_alert=True)
            else:
                # Channel lock is not set, just show the main menu
                _bot.delete_message(call.message.chat.id, call.message.message_id)
                from main import send_welcome 
                send_welcome(call.message)
    @_bot.callback_query_handler(func=lambda call: not call.from_user.is_bot and call.data.startswith(('buy_', 'select_', 'confirm_', 'cancel_')))
    def handle_purchase_callbacks(call):
        """هندل کردن دکمه‌های فرآیند خرید"""
        _bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        data = call.data
        messages = call.data
        # پاک کردن پیام قبلی
        try:
            _bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        if data.startswith("buy_select_server_"):
            server_id = int(data.replace("buy_select_server_", ""))
            select_server_for_purchase(user_id, server_id, call.message)
        elif data.startswith("buy_plan_type_"):
            select_plan_type(user_id, data.replace("buy_plan_type_", ""), call.message)
        elif data.startswith("buy_select_plan_"):
            plan_id = int(data.replace("buy_select_plan_", ""))
            select_fixed_plan(user_id, plan_id, call.message)
        elif data == "confirm_and_pay":
            display_payment_gateways(user_id, call.message)
        elif data.startswith("select_gateway_"):
            gateway_id = int(data.replace("select_gateway_", ""))
            select_payment_gateway(user_id, gateway_id, call.message)
        elif data.startswith("buy_select_profile_"):
            profile_id = int(data.replace("buy_select_profile_", ""))
            select_profile_for_purchase(user_id, profile_id, call.message)
          

        elif data == "cancel_order":
            _clear_user_state(user_id)
            _bot.edit_message_text(messages.ORDER_CANCELED, user_id, call.message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))


    @_bot.message_handler(content_types=['text', 'photo'], func=lambda msg: _user_states.get(msg.from_user.id))
    def handle_stateful_messages(message):
        """هندل کردن پیام‌های متنی یا عکسی که کاربر در یک وضعیت خاص ارسال می‌کند"""
        user_id = message.from_user.id
        state_info = _user_states[user_id]
        current_state = state_info.get('state')

        # حذف پیام ورودی کاربر برای تمیز ماندن چت
        try: _bot.delete_message(user_id, message.message_id)
        except Exception: pass

        if current_state == 'waiting_for_gigabytes_input':
            process_gigabyte_input(message)
        elif current_state == 'waiting_for_payment_receipt':
            process_payment_receipt(message)
        elif current_state == 'waiting_for_profile_gigabytes_input': 
            process_profile_gigabyte_input(message)
        elif current_state == 'waiting_for_payment_receipt':
            process_payment_receipt(message)
        elif current_state == 'waiting_for_custom_config_name':
            process_custom_config_name(message)
        elif current_state == 'waiting_for_charge_amount':
            process_charge_amount(message)
    # --- توابع کمکی و اصلی ---
    def show_how_to_connect(user_id, message):
        """Sends the guide on how to connect to the services."""
        _bot.edit_message_text(
            messages.HOW_TO_CONNECT_TEXT,
            user_id,
            message.message_id,
            reply_markup=inline_keyboards.get_back_button("user_main_menu"),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    def _clear_user_state(user_id):
        if user_id in _user_states:
            del _user_states[user_id]
        _bot.clear_step_handler_by_chat_id(chat_id=user_id)

    def _show_user_main_menu(user_id, message_to_edit=None):
        """ --- SIMPLIFIED: Fetches only the support link --- """
        _clear_user_state(user_id)
        menu_text = messages.USER_MAIN_MENU_TEXT
        
        # Fetch only the support link from the database
        support_link = _db_manager.get_setting('support_link')

        # Pass the link to the keyboard function
        menu_markup = inline_keyboards.get_user_main_inline_menu(support_link)
        
        if message_to_edit:
            try:
                _bot.edit_message_text(menu_text, user_id, message_to_edit.message_id, reply_markup=menu_markup)
            except telebot.apihelper.ApiTelegramException: pass
        else:
            _bot.send_message(user_id, menu_text, reply_markup=menu_markup)

    # --- فرآیند خرید ---
    def start_purchase(user_id, message):
        active_servers = [s for s in _db_manager.get_all_servers() if s['is_active'] and s['is_online']]
        if not active_servers:
            _bot.edit_message_text(messages.NO_ACTIVE_SERVERS_FOR_BUY, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        
        _user_states[user_id] = {'state': 'selecting_server', 'data': {}}
        _bot.edit_message_text(messages.SELECT_SERVER_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_server_selection_menu(active_servers))

    def select_server_for_purchase(user_id, server_id, message):
        _user_states[user_id]['data']['server_id'] = server_id
        _user_states[user_id]['state'] = 'selecting_plan_type'
        _bot.edit_message_text(messages.SELECT_PLAN_TYPE_PROMPT_USER, user_id, message.message_id, reply_markup=inline_keyboards.get_plan_type_selection_menu_user(server_id))
    
    def select_plan_type(user_id, plan_type, message):
        _user_states[user_id]['data']['plan_type'] = plan_type
        if plan_type == 'fixed_monthly':
            active_plans = [p for p in _db_manager.get_all_plans(only_active=True) if p['plan_type'] == 'fixed_monthly']
            if not active_plans:
                _bot.edit_message_text(messages.NO_FIXED_PLANS_AVAILABLE, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
                return
            _user_states[user_id]['state'] = 'selecting_fixed_plan'
            _bot.edit_message_text(messages.SELECT_FIXED_PLAN_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_fixed_plan_selection_menu(active_plans))
        
        elif plan_type == 'gigabyte_based':
            gb_plan = next((p for p in _db_manager.get_all_plans(only_active=True) if p['plan_type'] == 'gigabyte_based'), None)
            if not gb_plan or not gb_plan.get('per_gb_price'):
                _bot.edit_message_text(messages.GIGABYTE_PLAN_NOT_CONFIGURED, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
                return
            _user_states[user_id]['data']['gb_plan_details'] = gb_plan
            _user_states[user_id]['state'] = 'waiting_for_gigabytes_input'
            sent_msg = _bot.edit_message_text(messages.ENTER_GIGABYTES_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button(f"buy_select_server_{_user_states[user_id]['data']['server_id']}"))
            _user_states[user_id]['prompt_message_id'] = sent_msg.message_id

    def select_fixed_plan(user_id, plan_id, message):
        plan = _db_manager.get_plan_by_id(plan_id)
        if not plan:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
        _user_states[user_id]['data']['plan_details'] = plan
        show_order_summary(user_id, message)
        
    def process_gigabyte_input(message):
        user_id = message.from_user.id
        state_data = _user_states[user_id]
        
        if not is_float_or_int(message.text) or float(message.text) <= 0:
            _bot.edit_message_text(messages.INVALID_GIGABYTE_INPUT + "\n" + messages.ENTER_GIGABYTES_PROMPT, user_id, state_data['prompt_message_id'])
            return
            
        state_data['data']['requested_gb'] = float(message.text)
        show_order_summary(user_id, message)

    def show_order_summary(user_id, message):
        _user_states[user_id]['state'] = 'confirming_order'
        order_data = _user_states[user_id]['data']
        
        server_info = _db_manager.get_server_by_id(order_data['server_id'])
        summary_text = messages.ORDER_SUMMARY_HEADER
        summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info['name'])
        
        total_price = 0
        plan_details_for_admin = ""
        
        if order_data['plan_type'] == 'fixed_monthly':
            plan = order_data['plan_details']
            summary_text += messages.ORDER_SUMMARY_FIXED_PLAN.format(
                plan_name=plan['name'],
                volume_gb=plan['volume_gb'],
                duration_days=plan['duration_days']
            )
            total_price = plan['price']
            plan_details_for_admin = f"{plan['name']} ({plan['volume_gb']}GB, {plan['duration_days']} روز)"

        elif order_data['plan_type'] == 'gigabyte_based':
            gb_plan = order_data['gb_plan_details']
            requested_gb = order_data['requested_gb']
            total_price = requested_gb * gb_plan['per_gb_price']
            summary_text += messages.ORDER_SUMMARY_GIGABYTE_PLAN.format(gigabytes=requested_gb)
            plan_details_for_admin = f"{requested_gb} گیگابایت"

        summary_text += messages.ORDER_SUMMARY_TOTAL_PRICE.format(total_price=total_price)
        summary_text += messages.ORDER_SUMMARY_CONFIRM_PROMPT
        
        order_data['total_price'] = total_price
        order_data['plan_details_for_admin'] = plan_details_for_admin
        
        prompt_id = _user_states[user_id].get('prompt_message_id', message.message_id)
        _bot.edit_message_text(summary_text, user_id, prompt_id, reply_markup=inline_keyboards.get_order_confirmation_menu())

    # --- فرآیند پرداخت ---
    def display_payment_gateways(user_id, message):
        _user_states[user_id]['state'] = 'selecting_gateway'
        active_gateways = _db_manager.get_all_payment_gateways(only_active=True)
        if not active_gateways:
            _bot.edit_message_text(messages.NO_ACTIVE_PAYMENT_GATEWAYS, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("show_order_summary"))
            return
        
        _bot.edit_message_text(messages.SELECT_PAYMENT_GATEWAY_PROMPT, user_id, message.message_id, reply_markup=inline_keyboards.get_payment_gateway_selection_menu(active_gateways))
        
    def select_payment_gateway(user_id, gateway_id, message):
        gateway = _db_manager.get_payment_gateway_by_id(gateway_id)
        if not gateway:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return

        order_data = _user_states[user_id]['data']
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            logger.error(f"Could not find user with telegram_id {user_id} in the database.")
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
        # --- منطق تفکیک نوع درگاه ---
        if gateway['type'] == 'zarinpal':
            _bot.edit_message_text("⏳ در حال ساخت لینک پرداخت امن... لطفاً صبر کنید.", user_id, message.message_id)
            
            amount_toman = int(order_data['total_price'])
            
            # FIX: اطلاعات درگاه را به سفارش اضافه می‌کنیم تا در وب‌هوک قابل دسترس باشد
            order_data['gateway_details'] = gateway
            
            order_details_for_db = json.dumps(order_data)
            payment_id = _db_manager.add_payment(user_db_info['id'], amount_toman, message.message_id, order_details_for_db)
            
            if not payment_id:
                _bot.edit_message_text("❌ در ایجاد صورتحساب خطایی رخ داد.", user_id, message.message_id)
                return

            callback_url = f"https://{WEBHOOK_DOMAIN}/zarinpal/verify"
            
            payload = {
                "merchant_id": gateway['merchant_id'],
                "amount": amount_toman * 10, # FIX: تبدیل تومان به ریال
                "callback_url": callback_url,
                "description": f"خرید سرویس از ربات - سفارش شماره {payment_id}",
                "metadata": {"user_id": str(user_id), "payment_id": str(payment_id)}
            }
            
            try:
                response = requests.post(ZARINPAL_API_URL, json=payload, timeout=20)
                response.raise_for_status()
                result = response.json()

                if result.get("data") and result.get("data", {}).get("code") == 100:
                    authority = result['data']['authority']
                    payment_url = f"{ZARINPAL_STARTPAY_URL}{authority}"
                    _db_manager.set_payment_authority(payment_id, authority)
                    
                    # FIX: ساخت صحیح کیبورد با دو دکمه مجزا
                    markup = types.InlineKeyboardMarkup()
                    btn_pay = types.InlineKeyboardButton("🚀 پرداخت آنلاین", url=payment_url)
                    btn_back = types.InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="user_main_menu")
                    markup.add(btn_pay)
                    markup.add(btn_back)
                    
                    _bot.edit_message_text("لینک پرداخت شما ساخته شد. لطفاً از طریق دکمه زیر اقدام کنید.", user_id, message.message_id, reply_markup=markup)
                    _clear_user_state(user_id)
                else:
                    error_code = result.get("errors", {}).get("code", "نامشخص")
                    error_message = result.get("errors", {}).get("message", "خطای نامشخص از درگاه پرداخت")
                    _bot.edit_message_text(f"❌ خطا در ساخت لینک پرداخت: {error_message} (کد: {error_code})", user_id, message.message_id)

            except requests.exceptions.HTTPError as http_err:
                logger.error(f"HTTP error occurred: {http_err} - Response: {http_err.response.text}")
                _bot.edit_message_text("❌ درگاه پرداخت با خطای داخلی مواجه شد. لطفاً بعداً تلاش کنید.", user_id, message.message_id)
            except requests.exceptions.RequestException as e:
                logger.error(f"Error connecting to Zarinpal: {e}")
                _bot.edit_message_text("❌ امکان اتصال به درگاه پرداخت در حال حاضر وجود ندارد.", user_id, message.message_id)

        # --- منطق برای کارت به کارت ---
        elif gateway['type'] == 'card_to_card':
            _user_states[user_id]['data']['gateway_details'] = gateway
            _user_states[user_id]['state'] = 'waiting_for_payment_receipt'
            total_price = order_data['total_price']
            payment_text = messages.PAYMENT_GATEWAY_DETAILS.format(
                name=gateway['name'], card_number=gateway['card_number'],
                card_holder_name=gateway['card_holder_name'],
                description_line=f"**توضیحات:** {gateway['description']}\n" if gateway.get('description') else "",
                amount=total_price
            )
            sent_msg = _bot.edit_message_text(payment_text, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("show_order_summary"))
            _user_states[user_id]['prompt_message_id'] = sent_msg.message_id

    def process_payment_receipt(message):
        user_id = message.from_user.id
        state_data = _user_states.get(user_id)

        if not state_data or state_data.get('state') != 'waiting_for_payment_receipt':
            return

        if not message.photo:
            _bot.send_message(user_id, messages.INVALID_RECEIPT_FORMAT)
            return

        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.send_message(user_id, messages.OPERATION_FAILED)
            _clear_user_state(user_id)
            return

        order_data = state_data['data']
        
        server_id = None
        server_name = ""

        # تفکیک بین خرید پروفایل و خرید عادی
        if order_data.get('purchase_type') == 'profile':
            profile_details = order_data['profile_details']
            server_name = f"پروفایل: {profile_details['name']}"
            profile_inbounds = _db_manager.get_inbounds_for_profile(profile_details['id'], with_server_info=True)
            
            if profile_inbounds:
                # یک سرور را به عنوان نماینده برای ثبت در خرید انتخاب می‌کنیم
                server_id = profile_inbounds[0]['server']['id']
            else:
                _bot.send_message(user_id, "خطا: پروفایل انتخاب شده هیچ سروری ندارد. لطفاً به ادمین اطلاع دهید.")
                _clear_user_state(user_id)
                return
        else:
            # منطق خرید عادی
            server_id = order_data['server_id']
            server_info = _db_manager.get_server_by_id(server_id)
            server_name = server_info['name'] if server_info else "سرور ناشناس"

        order_details_for_db = {
            'user_telegram_id': user_id,
            'user_db_id': user_db_info['id'],
            'user_first_name': message.from_user.first_name,
            'server_id': server_id,
            'server_name': server_name,
            'purchase_type': order_data.get('purchase_type'),
            'plan_type': order_data.get('plan_type'),
            'profile_details': order_data.get('profile_details'),
            'plan_details': order_data.get('plan_details'),
            'gb_plan_details': order_data.get('gb_plan_details'),
            'requested_gb': order_data.get('requested_gb'),
            'total_price': order_data['total_price'],
            'gateway_name': order_data['gateway_details']['name'],
            'plan_details_text_display': order_data['plan_details_for_admin'],
            'receipt_file_id': message.photo[-1].file_id
        }

        payment_id = _db_manager.add_payment(
            user_db_info['id'],
            order_data['total_price'],
            message.message_id,
            json.dumps(order_details_for_db)
        )

        if not payment_id:
            _bot.send_message(user_id, "خطایی در ذخیره پرداخت شما رخ داد. لطفاً دوباره تلاش کنید.")
            _clear_user_state(user_id)
            return

        # ارسال نوتیفیکیشن به ادمین‌ها
        caption = messages.ADMIN_NEW_PAYMENT_NOTIFICATION_DETAILS.format(
            user_first_name=helpers.escape_markdown_v1(order_details_for_db['user_first_name']),
            user_telegram_id=order_details_for_db['user_telegram_id'],
            amount=order_details_for_db['total_price'],
            server_name=helpers.escape_markdown_v1(order_details_for_db['server_name']),
            plan_details=helpers.escape_markdown_v1(order_details_for_db['plan_details_text_display']),
            gateway_name=helpers.escape_markdown_v1(order_details_for_db['gateway_name'])
        )
        markup = inline_keyboards.get_admin_payment_action_menu(payment_id)
        
        for admin_id in ADMIN_IDS:
            try:
                sent_msg = _bot.send_photo(
                    admin_id,
                    order_details_for_db['receipt_file_id'],
                    caption=messages.ADMIN_NEW_PAYMENT_NOTIFICATION_HEADER + caption,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                if admin_id == ADMIN_IDS[0]:
                    _db_manager.update_payment_admin_notification_id(payment_id, sent_msg.message_id)
            except Exception as e:
                logger.error(f"Failed to send payment notification to admin {admin_id}: {e}")

        _bot.send_message(user_id, messages.RECEIPT_RECEIVED_USER)
        _clear_user_state(user_id)
        _show_user_main_menu(user_id)
    def show_service_details(user_id, purchase_id, message):
        """
        Shows the details of a specific subscription, without the single config button.
        """
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
            
        sub_link = ""
        server = _db_manager.get_server_by_id(purchase['server_id'])
        if server and purchase['sub_id']: # Use sub_id which is correct
            sub_base = server['subscription_base_url'].rstrip('/')
            sub_path = server['subscription_path_prefix'].strip('/')
            sub_link = f"{sub_base}/{sub_path}/{purchase['sub_id']}"
        
        if sub_link:
            text = messages.CONFIG_DELIVERY_HEADER + \
                messages.CONFIG_DELIVERY_SUB_LINK.format(sub_link=sub_link)
            
            # --- REMOVED: The button for single configs is gone ---
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🔙 بازگشت به سرویس‌ها", callback_data="user_my_services")
            markup.add(btn_back)

            _bot.edit_message_text(text, user_id, message.message_id, parse_mode='Markdown', reply_markup=markup)
            
            # Send QR Code as a new message
            try:
                import qrcode
                from io import BytesIO
                qr_image = qrcode.make(sub_link)
                bio = BytesIO()
                bio.name = 'qrcode.jpeg'
                qr_image.save(bio, 'JPEG')
                bio.seek(0)
                _bot.send_photo(user_id, bio, caption=messages.QR_CODE_CAPTION)
            except Exception as e:
                logger.error(f"Failed to generate QR code in service details: {e}")
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
    def send_single_configs(user_id, purchase_id):
        purchase = _db_manager.get_purchase_by_id(purchase_id)
        if not purchase or not purchase['single_configs_json']:
            _bot.send_message(user_id, messages.NO_SINGLE_CONFIGS_AVAILABLE)
            return
            
        configs = purchase['single_configs_json']
        text = messages.SINGLE_CONFIG_HEADER
        for config in configs:
            text += f"**{config['remark']} ({config['protocol']}/{config['network']})**:\n`{config['url']}`\n\n"
        
        _bot.send_message(user_id, text, parse_mode='Markdown')
        
        
    # در فایل handlers/user_handlers.py

    def show_order_summary(user_id, message):
        """
        خلاصه سفارش را برای سرویس عادی یا پروفایل نمایش می‌دهد. (نسخه نهایی و یکپارچه)
        """
        _user_states[user_id]['state'] = 'confirming_order'
        order_data = _user_states[user_id]['data']
        purchase_type = order_data.get('purchase_type')

        summary_text = messages.ORDER_SUMMARY_HEADER
        total_price = 0
        plan_details_for_admin = ""
        duration_text = "" # مقداردهی اولیه

        if purchase_type == 'profile':
            profile = order_data['profile_details']
            requested_gb = order_data['requested_gb']
            server_info = "چندین سرور" # چون پروفایل می‌تواند چند سروری باشد
            summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info)
            summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=profile['name'])
            summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=requested_gb)
            duration_text = f"{profile['duration_days']} روز"
            total_price = requested_gb * profile['per_gb_price']
            plan_details_for_admin = f"پروفایل: {profile['name']} ({requested_gb}GB)"

        else: # منطق قبلی برای خرید سرویس عادی
            server_info = _db_manager.get_server_by_id(order_data['server_id'])
            summary_text += messages.ORDER_SUMMARY_SERVER.format(server_name=server_info['name'])
            
            if order_data['plan_type'] == 'fixed_monthly':
                plan = order_data['plan_details']
                summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=plan['name'])
                summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=plan['volume_gb'])
                duration_text = f"{plan['duration_days']} روز"
                total_price = plan['price']
                plan_details_for_admin = f"{plan['name']} ({plan['volume_gb']}GB, {plan['duration_days']} روز)"

            elif order_data['plan_type'] == 'gigabyte_based':
                gb_plan = order_data['gb_plan_details']
                requested_gb = order_data['requested_gb']
                summary_text += messages.ORDER_SUMMARY_PLAN.format(plan_name=gb_plan['name'])
                summary_text += messages.ORDER_SUMMARY_VOLUME.format(volume_gb=requested_gb)
                duration_days = gb_plan.get('duration_days')
                duration_text = f"{duration_days} روز" if duration_days and duration_days > 0 else "نامحدود"
                total_price = requested_gb * gb_plan['per_gb_price']
                plan_details_for_admin = f"{gb_plan['name']} ({requested_gb}GB, {duration_text})"
        
        summary_text += messages.ORDER_SUMMARY_DURATION.format(duration_days=duration_text)
        summary_text += messages.ORDER_SUMMARY_TOTAL_PRICE.format(total_price=total_price)
        summary_text += messages.ORDER_SUMMARY_CONFIRM_PROMPT
        
        order_data['total_price'] = total_price
        order_data['plan_details_for_admin'] = plan_details_for_admin
        
        prompt_id = _user_states[user_id].get('prompt_message_id', message.message_id)
        _bot.edit_message_text(summary_text, user_id, prompt_id, parse_mode='Markdown', reply_markup=inline_keyboards.get_order_confirmation_menu())

    def handle_free_test_request(user_id, message):
        _bot.edit_message_text(messages.PLEASE_WAIT, user_id, message.message_id)
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id); return

        if _db_manager.check_free_test_usage(user_db_info['id']):
            _bot.edit_message_text(messages.FREE_TEST_ALREADY_USED, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu")); return

        active_servers = [s for s in _db_manager.get_all_servers() if s['is_active'] and s['is_online']]
        if not active_servers:
            _bot.edit_message_text(messages.NO_ACTIVE_SERVERS_FOR_BUY, user_id, message.message_id); return
        
        test_server_id = active_servers[0]['id']
        test_volume_gb = 0.1 # 100 MB
        test_duration_days = 1 # 1 day

        from utils.config_generator import ConfigGenerator
        config_gen = ConfigGenerator(_xui_api, _db_manager)
        client_details, sub_link, _ = config_gen.create_client_and_configs(user_id, test_server_id, test_volume_gb, test_duration_days)

        if sub_link:
            print("Free test subscription created successfully.")
            print(f"Subscription Link: {sub_link}")
            _db_manager.record_free_test_usage(user_db_info['id'])
            _bot.delete_message(user_id, message.message_id)
            _bot.send_message(user_id, messages.GET_FREE_TEST_SUCCESS)
            send_subscription_info(user_id, sub_link)
        else:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)



    def show_my_services_list(user_id, message):
        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_db_info:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return

        purchases = _db_manager.get_user_purchases(user_db_info['id'])
        
        _bot.edit_message_text(
            messages.MY_SERVICES_HEADER,
            user_id,
            message.message_id,
            reply_markup=inline_keyboards.get_my_services_menu(purchases),
            parse_mode='Markdown'
        )
        
        
    def process_custom_config_name(message):
        """
        نام دلخواه را پردازش کرده، با استفاده از ConfigGenerator جدید کانفیگ را ساخته،
        خرید را ثبت کرده و لینک اشتراک هوشمند را تحویل می‌دهد. (نسخه نهایی)
        """
        user_id = message.from_user.id
        state_info = _user_states.get(user_id, {})
        if not state_info or state_info.get('state') != 'waiting_for_custom_config_name':
            return

        custom_name = message.text.strip()
        if custom_name.lower() == 'skip':
            custom_name = None

        order_details = state_info['data']
        prompt_id = state_info['prompt_message_id']
        _bot.edit_message_text(messages.PLEASE_WAIT, user_id, prompt_id)

        server_id = order_details['server_id']
        plan_type = order_details['plan_type']
        total_gb, duration_days, plan_id = 0, 0, None

        if plan_type == 'fixed_monthly':
            plan = order_details['plan_details']
            total_gb, duration_days, plan_id = plan.get('volume_gb'), plan.get('duration_days'), plan.get('id')
        elif plan_type == 'gigabyte_based':
            gb_plan = order_details['gb_plan_details']
            total_gb = order_details['requested_gb']
            duration_days = gb_plan.get('duration_days', 0)
            plan_id = gb_plan.get('id')
        
        # --- اصلاح اصلی اینجاست: استفاده از متد جدید ConfigGenerator ---
        config_gen = ConfigGenerator(_db_manager)
        generated_configs, client_details = config_gen.create_subscription_for_server(
            user_telegram_id=user_id,
            server_id=server_id,
            total_gb=total_gb,
            duration_days=duration_days,
            custom_remark=custom_name
        )

        if not generated_configs:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, prompt_id)
            _clear_user_state(user_id)
            return

        user_db_info = _db_manager.get_user_by_telegram_id(user_id)
        expire_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)) if duration_days and duration_days > 0 else None
        
        # ساخت شناسه اشتراک هوشمند جدید
        new_sub_id = str(uuid.uuid4().hex)

        # ثبت خرید در دیتابیس با پارامترهای جدید
        _db_manager.add_purchase(
            user_id=user_db_info['id'],
            server_id=server_id,
            plan_id=plan_id,
            profile_id=None, # این یک خرید عادی است نه پروفایل
            expire_date=expire_date.strftime("%Y-%m-%d %H:%M:%S") if expire_date else None,
            initial_volume_gb=total_gb,
            client_uuids=client_details['uuids'], # ارسال لیست UUID ها
            client_email=client_details['email'],
            sub_id=new_sub_id,
            single_configs=generated_configs
        )

        _bot.delete_message(user_id, prompt_id)
        _bot.send_message(user_id, messages.SERVICE_ACTIVATION_SUCCESS_USER)
        
        # ساخت و ارسال لینک اشتراک هوشمند
        active_domain = _db_manager.get_active_subscription_domain()
        if not active_domain:
            _bot.send_message(user_id, "❌ دامنه فعالی برای لینک اشتراک تنظیم نشده است. لطفاً به پشتیبانی اطلاع دهید.")
            return

        final_sub_link = f"https://{active_domain['domain_name']}/sub/{new_sub_id}"
        send_subscription_info(_bot, user_id, final_sub_link)
        
        _clear_user_state(user_id)
    def show_platform_selection(user_id, message):
        """Shows the platform selection menu to the user."""
        platforms = _db_manager.get_distinct_platforms()
        if not platforms:
            _bot.edit_message_text("در حال حاضر هیچ آموزشی ثبت نشده است.", user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        markup = inline_keyboards.get_platforms_menu(platforms)
        _bot.edit_message_text("لطفاً پلتفرم خود را انتخاب کنید:", user_id, message.message_id, reply_markup=markup)

    def show_apps_for_platform(user_id, platform, message):
        """Shows the list of apps for the selected platform."""
        tutorials = _db_manager.get_tutorials_by_platform(platform)
        markup = inline_keyboards.get_apps_for_platform_menu(tutorials, platform)
        _bot.edit_message_text(f"آموزش کدام اپلیکیشن برای {platform} را می‌خواهید؟", user_id, message.message_id, reply_markup=markup)

    def send_tutorial_to_user(user_id, tutorial_id, message):
        """Forwards the selected tutorial message to the user."""
        tutorial = _db_manager.get_tutorial_by_id(tutorial_id) # You need to create this function in db_manager
        if not tutorial:
            _bot.answer_callback_query(message.id, "آموزش یافت نشد.", show_alert=True)
            return
        
        try:
            _bot.forward_message(
                chat_id=user_id,
                from_chat_id=tutorial['forward_chat_id'],
                message_id=tutorial['forward_message_id']
            )
            _bot.answer_callback_query(message.id)
        except Exception as e:
            logger.error(f"Failed to forward tutorial {tutorial_id} to user {user_id}: {e}")
            _bot.answer_callback_query(message.id, "خطا در ارسال آموزش. لطفاً به ادمین اطلاع دهید.", show_alert=True)
            
            
            
    def start_profile_purchase(user_id, message):
        """فرآیند خرید پروفایل را با نمایش لیست پروفایل‌های فعال شروع می‌کند."""
        active_profiles = _db_manager.get_all_profiles(only_active=True)
        if not active_profiles:
            _bot.edit_message_text(messages.NO_PROFILES_AVAILABLE, user_id, message.message_id, reply_markup=inline_keyboards.get_back_button("user_main_menu"))
            return
        
        # پاک کردن وضعیت قبلی کاربر
        _clear_user_state(user_id)
        
        markup = inline_keyboards.get_profile_selection_menu_for_user(active_profiles)
        _bot.edit_message_text(messages.SELECT_PROFILE_PROMPT, user_id, message.message_id, reply_markup=markup)
        
        
    def select_profile_for_purchase(user_id, profile_id, message):
        """
        اطلاعات پروفایل انتخاب شده را آماده کرده و از کاربر مقدار حجم را می‌پرسد.
        """
        
        profile = _db_manager.get_profile_by_id(profile_id)
        if not profile:
            _bot.edit_message_text(messages.OPERATION_FAILED, user_id, message.message_id)
            return
            
        # پاک کردن وضعیت قبلی و تنظیم وضعیت جدید برای دریافت حجم
        _clear_user_state(user_id)
        _user_states[user_id] = {
            'state': 'waiting_for_profile_gigabytes_input',
            'data': {
                'purchase_type': 'profile',
                'profile_details': dict(profile)
            }
        }
        
        # پرسیدن مقدار حجم از کاربر
        sent_msg = _bot.edit_message_text(
            messages.ENTER_PROFILE_GIGABYTES_PROMPT, 
            user_id, 
            message.message_id, 
            reply_markup=inline_keyboards.get_back_button("user_buy_profile")
        )
        _user_states[user_id]['prompt_message_id'] = sent_msg.message_id
    def process_profile_gigabyte_input(message):
        user_id = message.from_user.id
        state_data = _user_states[user_id]
        
        if not is_float_or_int(message.text) or float(message.text) <= 0:
            _bot.edit_message_text(f"{messages.INVALID_NUMBER_INPUT}\n\n{messages.ENTER_PROFILE_GIGABYTES_PROMPT}", user_id, state_data['prompt_message_id'])
            return
                
        state_data['data']['requested_gb'] = float(message.text)
        show_order_summary(user_id, message)
        
        
    def show_user_account_menu(user_id, message):
        """اطلاعات حساب کاربری را به کاربر نمایش می‌دهد."""
        user_info = _db_manager.get_user_by_telegram_id(user_id)
        if not user_info:
            _bot.edit_message_text("خطایی در دریافت اطلاعات شما رخ داد.", user_id, message.message_id)
            return

        balance = user_info.get('balance', 0.0)
        is_verified = user_info.get('is_verified', False)
        
        status_text = "تایید شده ✅" if is_verified else "نیاز به تکمیل پروفایل ⚠️"
        
        # TODO: در آینده تعداد زیرمجموعه‌ها را از دیتابیس می‌خوانیم
        referral_count = 0 
        
        account_text = (
            f"👤 **حساب کاربری شما**\n\n"
            f"▫️ **نام:** {helpers.escape_markdown_v1(user_info.get('first_name', ''))}\n"
            f"▫️ **آیدی عددی:** `{user_id}`\n"
            f"▫️ **موجودی کیف پول:** `{balance:,.0f}` تومان\n"
            f"▫️ **وضعیت حساب:** {status_text}\n\n"
            f"🔗 **لینک دعوت شما:**\n`t.me/{_bot.get_me().username}?start=ref_{user_id}`\n"
            f"👥 **تعداد زیرمجموعه‌ها:** {referral_count} نفر"
        )
        
        markup = inline_keyboards.get_user_account_menu()
        _show_menu(user_id, account_text, markup, message, parse_mode='Markdown')
        
        
        
    def start_add_balance_flow(user_id, message):
        """فرآیند شارژ کیف پول را با پرسیدن مبلغ شروع می‌کند."""
        _clear_user_state(user_id)
        prompt_text = "لطفاً مبلغی که می‌خواهید کیف پول خود را شارژ کنید به تومان وارد کنید (مثلاً: 50000):"
        prompt = _show_menu(user_id, prompt_text, inline_keyboards.get_back_button("user_account"), message)
        _user_states[user_id] = {'state': 'waiting_for_charge_amount', 'prompt_message_id': prompt.message_id}

    def process_charge_amount(message):
        """مبلغ وارد شده توسط کاربر را پردازش کرده و خلاصه سفارش را نمایش می‌دهد."""
        user_id = message.from_user.id
        state_info = _user_states.get(user_id, {})
        
        amount_str = message.text.strip()
        if not amount_str.isdigit() or int(amount_str) <= 0:
            _bot.send_message(user_id, "مبلغ وارد شده نامعتبر است. لطفاً یک عدد صحیح و مثبت وارد کنید.")
            return

        amount = int(amount_str)
        
        # ایجاد یک خلاصه سفارش موقت برای نمایش به کاربر و استفاده در فرآیند پرداخت
        state_info['data'] = {
            'purchase_type': 'wallet_charge',
            'total_price': amount,
            'plan_details_for_admin': f"شارژ کیف پول به مبلغ {amount:,.0f} تومان"
        }
        
        summary_text = (
            f"📝 **تایید تراکنش**\n\n"
            f"شما در حال شارژ کیف پول خود به مبلغ **{amount:,.0f} تومان** هستید.\n\n"
            f"آیا تایید می‌کنید؟"
        )
        
        markup = inline_keyboards.get_confirmation_menu("confirm_and_pay", "user_account")
        _bot.edit_message_text(summary_text, user_id, state_info['prompt_message_id'], reply_markup=markup, parse_mode='Markdown')