# keyboards/inline_keyboards.py

from telebot import types
import logging

logger = logging.getLogger(__name__)

# --- توابع کیبورد ادمین ---

def get_admin_main_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚙️ مدیریت سرورها", callback_data="admin_server_management"),
        types.InlineKeyboardButton("💰 مدیریت پلن‌ها", callback_data="admin_plan_management"),
        types.InlineKeyboardButton("💳 مدیریت درگاه‌ها", callback_data="admin_payment_management"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_user_management"),
        types.InlineKeyboardButton("🔗 مدیریت قفل کانال", callback_data="admin_channel_lock_management"),
        types.InlineKeyboardButton("📊 داشبورد", callback_data="admin_dashboard"),
        types.InlineKeyboardButton("💡 مدیریت آموزش‌ها", callback_data="admin_tutorial_management"),
        types.InlineKeyboardButton("📞 مدیریت پشتیبانی", callback_data="admin_support_management"),
        types.InlineKeyboardButton("🗂️ مدیریت پروفایل‌ها", callback_data="admin_profile_management"),
        types.InlineKeyboardButton("🌐 مدیریت دامنه‌ها", callback_data="admin_domain_management"),
        types.InlineKeyboardButton("⚙️ بررسی Nginx", callback_data="admin_check_nginx"),
        types.InlineKeyboardButton("🩺 بررسی وضعیت سیستم", callback_data="admin_health_check"),
        types.InlineKeyboardButton("👁️ مشاهده وضعیت DB", callback_data="admin_view_profile_db"),
        types.InlineKeyboardButton("🔧 بررسی لینک‌های Subscription", callback_data="admin_check_subscription_links"),
        types.InlineKeyboardButton("🎨 تنظیمات برندینگ", callback_data="admin_branding_settings"),
        types.InlineKeyboardButton("✍️ مدیریت پیام‌ها", callback_data="admin_message_management"),
        types.InlineKeyboardButton("⚙️ تنظیم وبهوک و دامنه", callback_data="admin_webhook_setup"),
        types.InlineKeyboardButton("📣 ارسال پیام همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🗄 تهیه نسخه پشتیبان", callback_data="admin_create_backup")
    )
    return markup

def get_server_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📝 لیست سرورها", callback_data="admin_list_servers"),
        types.InlineKeyboardButton("🔌 مدیریت Inboundها", callback_data="admin_manage_inbounds"),
        types.InlineKeyboardButton("🔄 تست اتصال سرورها", callback_data="admin_test_all_servers"),
        types.InlineKeyboardButton("❌ حذف سرور", callback_data="admin_delete_server"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
    )
    return markup
    
def get_plan_management_inline_menu():
    """ --- MODIFIED: Added Edit and Delete buttons --- """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن پلن", callback_data="admin_add_plan"),
        types.InlineKeyboardButton("📝 لیست پلن‌ها", callback_data="admin_list_plans"),
        types.InlineKeyboardButton("✏️ ویرایش پلن", callback_data="admin_edit_plan"), # <-- NEW
        types.InlineKeyboardButton("❌ حذف پلن", callback_data="admin_delete_plan"),     # <-- NEW
        types.InlineKeyboardButton("🔄 تغییر وضعیت پلن", callback_data="admin_toggle_plan_status"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
    )
    return markup

def get_payment_gateway_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن درگاه", callback_data="admin_add_gateway"),
        types.InlineKeyboardButton("📝 لیست درگاه‌ها", callback_data="admin_list_gateways"),
        types.InlineKeyboardButton("🔄 تغییر وضعیت درگاه", callback_data="admin_toggle_gateway_status"),
        types.InlineKeyboardButton("✏️ ویرایش درگاه", callback_data="admin_edit_gateway"),
        types.InlineKeyboardButton("🗑️ حذف درگاه", callback_data="admin_delete_gateway"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
    )
    return markup
    
def get_user_management_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست همه کاربران", callback_data="admin_list_users"),
        types.InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
    )
    return markup

def get_plan_type_selection_menu_admin():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("ماهانه (Fixed)", callback_data="plan_type_fixed_monthly"),
        types.InlineKeyboardButton("حجمی (Gigabyte)", callback_data="plan_type_gigabyte_based"),
        types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_plan_management")
    )
    return markup
    
    
def get_inbound_selection_menu(server_id: int, panel_inbounds: list, active_inbound_ids: list):
    """
    منوی انتخاب اینباندها با ترفند ضد-کش (anti-cache) برای اطمینان از آپدیت شدن.
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ انتخاب همه", callback_data=f"inbound_select_all_{server_id}"),
        types.InlineKeyboardButton("⬜️ لغو انتخاب همه", callback_data=f"inbound_deselect_all_{server_id}")
    )

    for inbound in panel_inbounds:
        inbound_id = inbound['id']
        is_active = inbound_id in active_inbound_ids
        emoji = "✅" if is_active else "⬜️"
        button_text = f"{emoji} {inbound.get('remark', f'Inbound {inbound_id}')}"
        
        # --- ترفند اصلی ---
        # یک پارامتر اضافی (is_active) به callback_data اضافه می‌کنیم
        # این باعث می‌شود callback_data در هر حالت (فعال/غیرفعال) متفاوت باشد
        callback_data = f"inbound_toggle_{server_id}_{inbound_id}_{1 if is_active else 0}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
    markup.add(
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_server_management"),
        types.InlineKeyboardButton("✔️ ثبت تغییرات", callback_data=f"inbound_save_{server_id}")
    )
    return markup

def get_confirmation_menu(confirm_callback: str, cancel_callback: str, confirm_text="✅ بله", cancel_text="❌ خیر"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
        types.InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
    )
    return markup

# --- توابع کیبورد کاربر ---

def get_user_main_inline_menu(support_link: str):
    """ --- نسخه آپدیت شده با دکمه پروفایل --- """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 خرید سرویس عادی", callback_data="user_buy_service"),
        types.InlineKeyboardButton("🗂️ خرید پروفایل", callback_data="user_buy_profile"),
        types.InlineKeyboardButton("🎁 اکانت تست رایگان", callback_data="user_free_test"),
        types.InlineKeyboardButton("🗂️ سرویس‌های من", callback_data="user_my_services"),
        types.InlineKeyboardButton("👤 حساب کاربری", callback_data="user_account"),
        types.InlineKeyboardButton("💡 آموزش اتصال", callback_data="user_how_to_connect")
    )

    if support_link and support_link.startswith('http'):
        markup.add(types.InlineKeyboardButton("📞 پشتیبانی", url=support_link))
        
    return markup
    
def get_back_button(callback_data: str, text: str = "🔙 بازگشت"):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))
    return markup

def get_server_selection_menu(servers: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for server in servers:
        markup.add(types.InlineKeyboardButton(server['name'], callback_data=f"buy_select_server_{server['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منو", callback_data="user_main_menu"))
    return markup
    
def get_plan_type_selection_menu_user(server_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("ماهانه (Fixed)", callback_data="buy_plan_type_fixed_monthly"),
        types.InlineKeyboardButton("حجمی (Gigabyte)", callback_data="buy_plan_type_gigabyte_based")
    )
    markup.add(get_back_button(f"user_buy_service").keyboard[0][0]) # Add back button
    return markup

def get_fixed_plan_selection_menu(plans: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for plan in plans:
        button_text = f"{plan['name']} - {plan['volume_gb']:.1f}GB / {plan['duration_days']} روز - {plan['price']:,.0f} تومان"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_select_plan_{plan['id']}"))
    markup.add(get_back_button("user_buy_service").keyboard[0][0]) # Back to server selection
    return markup
    
def get_order_confirmation_menu():
    return get_confirmation_menu(
        confirm_callback="confirm_and_pay",
        cancel_callback="cancel_order",
        confirm_text="✅ تأیید و پرداخت",
        cancel_text="❌ انصراف"
    )

def get_payment_gateway_selection_menu(gateways: list, wallet_balance: float = 0, order_price: float = 0):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # --- منطق جدید برای نمایش دکمه کیف پول ---
    if wallet_balance >= order_price:
        balance_str = f"{wallet_balance:,.0f}"
        btn_text = f"💳 پرداخت از کیف پول (موجودی: {balance_str} تومان)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data="pay_with_wallet"))

    # نمایش بقیه درگاه‌ها
    for gateway in gateways:
        markup.add(types.InlineKeyboardButton(gateway['name'], callback_data=f"select_gateway_{gateway['id']}"))
        
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به خلاصه سفارش", callback_data="show_order_summary"))
    return markup
    
def get_admin_payment_action_menu(payment_id: int):
    return get_confirmation_menu(
        confirm_callback=f"admin_approve_payment_{payment_id}",
        cancel_callback=f"admin_reject_payment_{payment_id}",
        confirm_text="✅ تأیید پرداخت",
        cancel_text="❌ رد کردن"
    )
    
def get_single_configs_button(purchase_id: int):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📄 دریافت کانفیگ‌های تکی", callback_data=f"user_get_single_configs_{purchase_id}"))
    return markup

def get_my_services_menu(purchases: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not purchases:
        markup.add(types.InlineKeyboardButton("شما سرویس فعالی ندارید", callback_data="no_action"))
    else:
        for p in purchases:
            status_emoji = "✅" if p['is_active'] else "❌"
            
            # --- THE FIX IS HERE ---
            if p['expire_date']:
                # First, format the datetime object into a YYYY-MM-DD string
                expire_date_str = p['expire_date'].strftime('%Y-%m-%d')
            else:
                expire_date_str = "نامحدود"
            # --- End of fix ---

            btn_text = f"{status_emoji} سرویس {p['id']} ({p.get('server_name', 'N/A')}) - انقضا: {expire_date_str}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"user_service_details_{p['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منو اصلی", callback_data="user_main_menu"))
    return markup



# در فایل keyboards/inline_keyboards.py





def get_gateway_type_selection_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 کارت به کارت", callback_data="gateway_type_card_to_card"),
        types.InlineKeyboardButton("🟢 زرین‌پال", callback_data="gateway_type_zarinpal")
    )
    markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_payment_management"))
    return markup


def get_channel_lock_management_menu(channel_set: bool):
    """Creates the menu for managing the required channel."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ ثبت/تغییر کانال", callback_data="admin_set_channel_lock"))
    if channel_set:
        markup.add(types.InlineKeyboardButton("❌ حذف قفل کانال", callback_data="admin_remove_channel_lock"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup

def get_user_management_menu():
    """Creates the main menu for user management."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="admin_search_user"))
    # Add more user management options here later if needed
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup

def get_user_subscriptions_management_menu(db_manager, purchases: list, user_telegram_id: int):
    """
    --- MODIFIED: Accepts db_manager as a parameter to fetch server names ---
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not purchases:
        markup.add(types.InlineKeyboardButton("این کاربر اشتراک فعالی ندارد", callback_data="no_action"))
    else:
        for p in purchases:
            # Now we use the passed db_manager to get server info
            server = db_manager.get_server_by_id(p['server_id'])
            server_name = server['name'] if server else "N/A"
            expire_str = p['expire_date'][:10] if p['expire_date'] else "نامحدود"
            btn_text = f"❌ حذف سرویس {p['id']} ({server_name} - {expire_str})"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_purchase_{p['id']}_{user_telegram_id}"))
            
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به مدیریت کاربران", callback_data="admin_user_management"))
    return markup


def get_join_channel_keyboard(channel_link: str):
    """
    --- NEW: Creates the keyboard for the channel lock message ---
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Button to join the channel (as a URL)
    markup.add(types.InlineKeyboardButton("🚀 عضویت در کانال", url=channel_link))
    # Button to check membership status again
    markup.add(types.InlineKeyboardButton("✅ عضو شدم و بررسی مجدد", callback_data="user_check_join_status"))
    return markup



def get_tutorial_management_menu():
    """Creates the menu for managing tutorials."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ افزودن آموزش", callback_data="admin_add_tutorial"))
    markup.add(types.InlineKeyboardButton("📝 لیست و حذف آموزش‌ها", callback_data="admin_list_tutorials"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup

def get_tutorials_list_menu(tutorials: list):
    """Displays a list of tutorials with delete buttons."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not tutorials:
        markup.add(types.InlineKeyboardButton("هیچ آموزشی ثبت نشده است", callback_data="no_action"))
    else:
        for t in tutorials:
            btn_text = f"❌ حذف: {t['platform']} - {t['app_name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_tutorial_{t['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_tutorial_management"))
    return markup

def get_platforms_menu(platforms: list):
    """Creates a menu for users to select a platform."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(p, callback_data=f"user_select_platform_{p}") for p in platforms]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="user_main_menu"))
    return markup

def get_apps_for_platform_menu(tutorials: list, platform: str):
    """Creates a menu for users to select an app for a specific platform."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for t in tutorials:
        markup.add(types.InlineKeyboardButton(t['app_name'], callback_data=f"user_select_tutorial_{t['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پلتفرم‌ها", callback_data="user_how_to_connect"))
    return markup



def get_support_management_menu(): # The 'support_type' argument has been removed
    """--- SIMPLIFIED: Creates a simple menu for setting the support link ---"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ ثبت/ویرایش لینک پشتیبانی", callback_data="admin_edit_support_link"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup




def get_panel_type_selection_menu():
    """کیبورد انتخاب نوع پنل هنگام افزودن سرور جدید را می‌سازد."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("3x-ui (standard)", callback_data="panel_type_x-ui"),
        types.InlineKeyboardButton("Alireza-x-ui", callback_data="panel_type_alireza"),
        # types.InlineKeyboardButton("Hiddify", callback_data="panel_type_hiddify"), # برای آینده
        types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_server_management")
    )
    return markup



def get_profile_management_inline_menu():
    """منوی اصلی برای مدیریت پروفایل‌ها را ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن پروفایل", callback_data="admin_add_profile"),
        types.InlineKeyboardButton("📝 لیست پروفایل‌ها", callback_data="admin_list_profiles"),
        types.InlineKeyboardButton("🔗 مدیریت اینباندهای پروفایل", callback_data="admin_manage_profile_inbounds"),
        types.InlineKeyboardButton("❌ حذف پروفایل", callback_data="admin_delete_profile"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
    )
    return markup



def get_profile_selection_menu(profiles):
    """یک منو برای انتخاب از بین پروفایل‌های موجود ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for profile in profiles:
        btn_text = f"🗂️ {profile['name']} (ID: {profile['id']})"
        callback_data = f"admin_select_profile_{profile['id']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_profile_management"))
    return markup


def get_server_selection_menu_for_profile(servers, profile_id):
    """یک منو برای انتخاب سرور جهت افزودن اینباند به پروفایل ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for server in servers:
        btn_text = f"⚙️ {server['name']} (ID: {server['id']})"
        # ما آیدی پروفایل را هم در callback_data پاس می‌دهیم تا در مرحله بعد به آن دسترسی داشته باشیم
        callback_data = f"admin_ps_{profile_id}_{server['id']}" # ps = Profile Server
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به انتخاب پروفایل", callback_data="admin_manage_profile_inbounds"))
    return markup



def get_inbound_selection_menu_for_profile(profile_id, server_id, panel_inbounds, selected_inbound_ids):
    """منوی چک‌لیست برای انتخاب اینباندها برای یک پروفایل خاص را ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for inbound in panel_inbounds:
        inbound_id = inbound['id']
        is_selected = inbound_id in selected_inbound_ids
        emoji = "✅" if is_selected else "⬜️"
        button_text = f"{emoji} {inbound.get('remark', f'Inbound {inbound_id}')}"
        
        # callback_data شامل آیدی پروفایل، سرور و اینباند است
        callback_data = f"admin_pi_toggle_{profile_id}_{server_id}_{inbound_id}" # pi = Profile Inbound
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
    markup.add(
        types.InlineKeyboardButton("✔️ ثبت تغییرات برای این سرور", callback_data=f"admin_pi_save_{profile_id}_{server_id}")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به انتخاب سرور", callback_data=f"admin_select_profile_{profile_id}"))
    return markup



def get_profile_selection_menu_for_user(profiles):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for profile in profiles:
        btn_text = f"🗂️ {profile['name']} (هر گیگ: {profile['per_gb_price']:,.0f} تومان)"
        callback_data = f"buy_select_profile_{profile['id']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منو", callback_data="user_main_menu"))
    return markup




def get_domain_management_menu(domains):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ افزودن دامنه جدید", callback_data="admin_add_domain"))
    
    if domains:
        markup.add(types.InlineKeyboardButton("--- دامنه‌های ثبت شده ---", callback_data="no_action"))
        for domain in domains:
            status = " (فعال ✅)" if domain['is_active'] else ""
            ssl_emoji = "🌐" if domain.get('ssl_status') else "⚠️"
            
            btn_text_activate = f"{ssl_emoji} فعال‌سازی: {domain['domain_name']}{status}"
            btn_text_delete = "❌ حذف"
            
            markup.add(
                types.InlineKeyboardButton(btn_text_activate, callback_data=f"admin_activate_domain_{domain['id']}"),
                types.InlineKeyboardButton(btn_text_delete, callback_data=f"admin_delete_domain_{domain['id']}")
            )

    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup


def get_admin_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="admin_add_admin"),
        types.InlineKeyboardButton("❌ حذف ادمین", callback_data="admin_remove_admin")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup


def get_template_management_menu(all_active_inbounds):
    """
    منوی مدیریت الگوها را با نمایش وضعیت هر اینباند ایجاد می‌کند.
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_active_inbounds:
        markup.add(types.InlineKeyboardButton("هیچ اینباند فعالی یافت نشد", callback_data="no_action"))
    else:
        for inbound in all_active_inbounds:
            status_emoji = "✅" if inbound.get('config_params') else "⚠️"
            
            # --- اصلاح اصلی در این خط انجام شده است ---
            inbound_remark = inbound.get('remark', f"ID: {inbound['inbound_id']}")
            
            btn_text = (
                f"{status_emoji} {inbound['server_name']} - {inbound_remark}"
            )
            # callback_data شامل آیدی سرور و اینباند است تا بدانیم کدام الگو را باید ویرایش کنیم
            callback_data = f"admin_edit_template_{inbound['server_id']}_{inbound['inbound_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
            
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_server_management"))
    return markup


def get_profile_template_management_menu(all_profile_inbounds):
    """
    منوی مدیریت الگوها برای پروفایل‌ها را ایجاد می‌کند.
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_profile_inbounds:
        markup.add(types.InlineKeyboardButton("هیچ اینباندی به پروفایل‌ها متصل نیست", callback_data="no_action"))
    else:
        current_profile = None
        for inbound in all_profile_inbounds:
            # برای خوانایی، نام پروفایل را به عنوان تیتر نمایش می‌دهیم
            if current_profile != inbound['profile_name']:
                current_profile = inbound['profile_name']
                markup.add(types.InlineKeyboardButton(f"--- پروفایل: {current_profile} ---", callback_data="no_action"))

            status_emoji = "✅" if inbound.get('config_params') else "⚠️"
            
            # --- اصلاح اصلی در این دو خط انجام شده است ---
            inbound_remark = inbound.get('remark', f"ID: {inbound['inbound_id']}")
            btn_text = (
                f"{status_emoji} {inbound['server_name']} - {inbound_remark}"
            )
            
            callback_data = f"admin_edit_profile_template_{inbound['profile_id']}_{inbound['server_id']}_{inbound['inbound_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
            
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_profile_management"))
    return markup



def get_user_account_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ افزایش موجودی", callback_data="user_add_balance"),
        types.InlineKeyboardButton("📝 تکمیل پروفایل", callback_data="user_complete_profile")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="user_main_menu"))
    return markup


def get_message_management_menu(messages_on_page, current_page, total_pages):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for msg in messages_on_page:
        preview_text = msg['message_text'][:30].replace('\n', ' ') + "..."
        btn_text = f"✏️ {msg['message_key']} | {preview_text}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_edit_msg_{msg['message_key']}"))
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ قبل", callback_data=f"admin_msg_page_{current_page - 1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="no_action"))
    if current_page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("بعد ➡️", callback_data=f"admin_msg_page_{current_page + 1}"))
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)
        
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu"))
    return markup


def get_manage_user_menu(user_telegram_id):
    """پنل مدیریت برای یک کاربر خاص را ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تغییر نقش", callback_data=f"admin_change_role_{user_telegram_id}"),
        types.InlineKeyboardButton("💰 تنظیم موجودی", callback_data=f"admin_adjust_balance_{user_telegram_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🗂️ مشاهده اشتراک‌ها", callback_data=f"admin_view_subs_{user_telegram_id}")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_user_management")
    )
    return markup


def get_change_role_menu(user_telegram_id):
    """منوی انتخاب نقش جدید برای یک کاربر را ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    roles = {
        'admin': '👑 مدیر',
        'reseller': '🤝 نماینده',
        'user': '👤 کاربر'
    }
    for role_key, role_name in roles.items():
        markup.add(types.InlineKeyboardButton(
            f"تنظیم به: {role_name}", 
            callback_data=f"admin_set_role_{user_telegram_id}_{role_key}"
        ))

    # دکمه بازگشت به پنل مدیریت همین کاربر
    # ما یک callback جدید برای این کار تعریف می‌کنیم
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_manage_user_{user_telegram_id}"))
    return markup

def get_admin_subs_list_menu(user_telegram_id):
    """یک دکمه بازگشت به پنل مدیریت کاربر خاص ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(
        "🔙 بازگشت به پنل کاربر", 
        callback_data=f"admin_manage_user_{user_telegram_id}"
    ))
    return markup


def get_broadcast_confirmation_menu():
    """کیبورد تایید نهایی برای ارسال پیام همگانی را ایجاد می‌کند."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ ارسال نهایی", callback_data="admin_confirm_broadcast"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="admin_cancel_broadcast")
    )
    return markup


def get_gateway_selection_menu_for_edit(gateways: list):
    """منوی انتخاب درگاه برای ویرایش"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not gateways:
        markup.add(types.InlineKeyboardButton("❌ هیچ درگاهی یافت نشد", callback_data="no_action"))
    else:
        for gateway in gateways:
            status_emoji = "✅" if gateway.get('is_active', False) else "❌"
            gateway_type_emoji = "💳" if gateway.get('type') == 'card_to_card' else "🟢"
            btn_text = f"{status_emoji} {gateway_type_emoji} {gateway['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_edit_gateway_{gateway['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_payment_management"))
    return markup


def get_gateway_selection_menu_for_delete(gateways: list):
    """منوی انتخاب درگاه برای حذف"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not gateways:
        markup.add(types.InlineKeyboardButton("❌ هیچ درگاهی یافت نشد", callback_data="no_action"))
    else:
        for gateway in gateways:
            status_emoji = "✅" if gateway.get('is_active', False) else "❌"
            gateway_type_emoji = "💳" if gateway.get('type') == 'card_to_card' else "🟢"
            btn_text = f"{status_emoji} {gateway_type_emoji} {gateway['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_delete_gateway_{gateway['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_payment_management"))
    return markup


def get_gateway_delete_confirmation_menu(gateway_id: int, gateway_name: str):
    """منوی تایید حذف درگاه"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_confirm_delete_gateway_{gateway_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="admin_payment_management")
    )
    return markup


def get_user_purchases_menu(purchases):
    """منوی خریدهای کاربر"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for purchase in purchases:
        # نمایش اطلاعات خرید
        purchase_info = f"📦 {purchase['id']} - {purchase.get('server_name', 'N/A')}"
        if purchase.get('expire_date'):
            from datetime import datetime
            expire_date = purchase['expire_date']
            if isinstance(expire_date, str):
                expire_date = datetime.strptime(expire_date, '%Y-%m-%d %H:%M:%S')
            days_left = (expire_date - datetime.now()).days
            status = "✅ فعال" if days_left > 0 else "❌ منقضی"
            purchase_info += f" ({status})"
        
        # دکمه‌های عملیات
        markup.add(
            types.InlineKeyboardButton(
                purchase_info, 
                callback_data=f"admin_view_purchase_{purchase['id']}"
            )
        )
        
        # دکمه‌های اضافی
        markup.add(
            types.InlineKeyboardButton(
                "🔄 بروزرسانی کانفیگ", 
                callback_data=f"admin_update_configs_{purchase['id']}"
            ),
            types.InlineKeyboardButton(
                "📊 جزئیات", 
                callback_data=f"admin_purchase_details_{purchase['id']}"
            )
        )
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_user_management"))
    return markup