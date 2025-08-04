# api_client/alireza_api_client.py

import requests
import logging
import json

# غیرفعال کردن هشدارهای مربوط به SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AlirezaAPIClient:
    def __init__(self, panel_url, username, password):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        self.api_base_path = "/xui/API/inbounds" # مسیر استاندارد علیرضا
        logger.info(f"AlirezaAPIClient initialized for {self.base_url}")
    def _request(self, method, path, **kwargs):
        """یک متد مرکزی برای ارسال تمام درخواست‌ها."""
        if not path.startswith('/'):
            path = '/' + path
        
        if not self.is_logged_in and path != '/login':
            if not self.login():
                return None

        url = self.base_url + path
        try:
            response = self.session.request(method, url, verify=False, timeout=20, **kwargs)
            if response.status_code in [401, 403]:
                logger.warning("Authentication error. Re-logging in...")
                if not self.login(): return None
                response = self.session.request(method, url, verify=False, timeout=20, **kwargs)

            response.raise_for_status()
            if not response.text:
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Request failed for {path}: {e}")
            return None

    def login(self):
        """ --- FINAL VERSION: Smart cookie detection --- """
        self.is_logged_in = False
        payload = {'username': self.username, 'password': self.password}
        response_data = self._request('post', '/login', data=payload)
        
        if response_data and response_data.get('success'):
            # --- THE FIX IS HERE ---
            # We use the same robust check here.
            if self.session.cookies:
                self.is_logged_in = True
                cookie_names = '; '.join([f'{c.name}' for c in self.session.cookies])
                logger.info(f"Successfully logged in. Found session cookie(s): {cookie_names}")
                return True
            else:
                logger.error("Login API call was successful, but the panel did not return any session cookie.")
                return False
        else:
            logger.error(f"Login failed for {self.base_url}.")
            return False

    def check_login(self):
        """بررسی اعتبار لاگین."""
        if self.is_logged_in:
            return True
        return self.login()

    def add_client(self, data):
        """یک کلاینت جدید به یک اینباند مشخص اضافه می‌کند."""
        logger.info(f"Adding client to inbound {data.get('id')}...")
        full_path = self.api_base_path + "/addClient/"
        response_data = self._request('post', full_path, json=data)
        
        if response_data and response_data.get('success'):
            logger.info(f"Client added successfully.")
            return True
        
        error_msg = response_data.get('msg', 'Unknown error') if response_data else "No response"
        logger.error(f"Failed to add client. Reason: {error_msg}")
        return False

    def get_inbound(self, inbound_id):
        """اطلاعات یک اینباند خاص را دریافت می‌کند."""
        full_path = f"{self.api_base_path}/get/{inbound_id}"
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj')
        return None

    def list_inbounds(self):
        """لیست تمام اینباندها را دریافت می‌کند."""
        full_path = self.api_base_path + "/"
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj', [])
        return []